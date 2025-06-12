-- Bind static classes from java
StandardCharsets = luajava.bindClass("java.nio.charset.StandardCharsets")
JCasUtil = luajava.bindClass("org.apache.uima.fit.util.JCasUtil")
Sentence = luajava.bindClass("de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence")

------------------------------------------------------

---Indicates that this component supports the "new" `process` method.
SUPPORTS_PROCESS = true
---Indicates that this component does NOT support the old `serialize`/`deserialize` methods.
SUPPORTS_SERIALIZE = false

------------------------------------------------------
--- Below are two general purpose functions for batch processing of annotations in a JCas.
--- These are not specific for this component, but only support a simple Iterator as input.

---Create and yield batches of elements from an iterator after applying a transform function.
---@param iterator any an iterator over annotations
---@param transform fun(any): any a tranform function over the elements of the iterator
---@param batch_size integer size of each batch sent to the component
function get_batches(iterator, transform, batch_size)
    local batch = {}
    while iterator:hasNext() do
        batch[#batch + 1] = transform(iterator:next())
        if #batch == batch_size then
            coroutine.yield(batch)
            batch = {}
        end
    end

    if #batch > 0 then
        coroutine.yield(batch)
    end
end

---Iterate over batches of elements from an iterator after applying a transform function.
---@param iterator any an iterator over annotations
---@param transform fun(any): any a tranform function over the elements of the iterator
---@param batch_size integer size of each batch
---@return fun(): table an iterator over batches to process
function batched(iterator, transform, batch_size)
    local co = coroutine.create(function() get_batches(iterator, transform, batch_size) end)
    return function()
        local _, batch = coroutine.resume(co)
        return batch
    end
end

------------------------------------------------------

---Get the text and offset (begin index) of a sentence.
---@param sentence any a sentence annotation
---@return table a table with the text and offset of the sentence
function get_sentence_and_offset(sentence)
    return {
        text = sentence:getCoveredText(),
        offset = sentence:getBegin(),
    }
end

---Split a string by commas into a table of stringsl, while stripping whitespaces and dropping empty strings.
---@param str string a string to split by commas
---@return table<integer, string> a table of strings
local function split_comma(str)
    ---Split a string by commas and return a table of strings.
    ---This is used to parse the `spacy_disable` parameter.
    local result = {}
    for part in str:gmatch("[^,%s]+") do
        table.insert(result, part)
    end
    return result
end

---We can define settings here or we could fetch them from the component using separate endpoints.
REQUEST_BATCH_SIZE = 1024

---Process the sentences in the given JCas in small batches.
---@param sourceCas any JCas (view) to process
---@param handler any DuuiHttpRequestHandler with a connection to the running component
---@param parameters table<string, string> optional parameters
---@param targetCas any JCas (view) to write the results to (optional)
function process(sourceCas, handler, parameters, targetCas)
    parameters = parameters or {}
    local language = sourceCas:getDocumentLanguage()
    if language == nil or language == "" or language == "x-unspecified" then
        language = parameters.spacy_language
    end
    local config = {
        spacy_language = language,
        spacy_model_size = parameters.spacy_model_size or "lg",
        spacy_batch_size = tonumber(parameters.spacy_batch_size) or 32,
        spacy_disable = split_comma(parameters.spacy_disable or ""),
    }

    targetCas = targetCas or sourceCas

    ---If there are no sentences in the source JCas (view), we can call the supplementary /eos
    ---endpoint of the component to annotate them. The spaCy `senter` pipeline component can deal
    ---with much larger inputs than the other components, so we can use the whole document text.
    local sentences = JCasUtil:select(sourceCas, Sentence)

    if sentences:isEmpty() then
        local response = handler:post("/eos", json.encode({
            text = sourceCas:getDocumentText(),
            config = config,
        }))
        process_eos(targetCas, response)
        sentences = JCasUtil:select(targetCas, Sentence)

        if sentences:isEmpty() then
            error("No sentences found in the source or target JCas.")
        end
    end

    ---After fetching the sentences (and possibly annotating them), we can process them in batches.
    ---The batch size is variable, here we use a fixed batch size in number of sentences.
    ---Developers could also implement dynamic batch sizes depending on information provided by the
    ---component or on the length of the text etc.
    ---Using the `get_sentence_and_offset` transform function, we just get the text and offset of each
    ---sentence. The general purpose batching functions from above deal with the rest.
    ---After the component has processed the sentences, we call `process_response` on the response directly.

    local batch_size = tonumber(parameters.request_batch_size) or REQUEST_BATCH_SIZE
    ---@type table<integer, any> table to aggregate references to created annotations
    local references = {}
    ---@type table<string, table>
    local results = {}
    for batch in batched(sentences:iterator(), get_sentence_and_offset, batch_size) do
        if type(batch) ~= "table" then
            error("Error while batching: " .. batch)
        end

        ---@type any DuuiHttpRequestHandler.Response{int statusCode, byte[]? body}
        local response = handler:process(
            json.encode({
                sentences = batch,
                config = config,
            })
        )

        ---The response wraps the HTTP status code and body in a record class.
        ---If there is an error, we can deal with it here. We could also make use of additional information
        ---provided by the component, e.g. the error message in the body.
        ---Here, we just throw an error with the status code and body.

        if response:statusCode() ~= 200 then
            error("Error " .. response:statusCode() .. " in communication with component: " .. response:bodyUtf8())
        end

        ---The Response object provides a method to decode the body as UTF-8, which we then decode as JSON.
        results = json.decode(response:bodyUtf8())

        ---We collect all annotation references in a single table to deduplicate the annotator metadata annotation.

        local batch_refs = process_response(targetCas, results)
        for _, ref in ipairs(batch_refs) do
            references[#references + 1] = ref
        end
    end

    ---After processing all sentences, we can add the metadata to the target JCas.
    ---The metadata is provided by the component in the response, so we can just use it here.

    if results.metadata ~= nil then
        add_annotator_metadata(targetCas, results.metadata, references)
    else
        warn("last response did not contain metadata, cannot add SpacyAnnotatorMetaData annotation")
    end
end

---A lookup table for dependency types, mapping upper-case dependency types to their
---corresponding Java class names.
---@type table<stringlib, string>
DEP_TYPE_LOOKUP = {
    ROOT = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.ROOT",
    ABBREV = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.ABBREV",
    ACOMP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.ACOMP",
    ADVCL = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.ADVCL",
    ADVMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.ADVMOD",
    AGENT = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.AGENT",
    AMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.AMOD",
    APPOS = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.APPOS",
    ATTR = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.ATTR",
    AUX0 = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.AUX0",
    AUXPASS = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.AUXPASS",
    CC = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.CC",
    CCOMP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.CCOMP",
    COMPLM = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.COMPLM",
    CONJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.CONJ",
    CONJ_YET = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.CONJ_YET",
    CONJP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.CONJP",
    COP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.COP",
    CSUBJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.CSUBJ",
    CSUBJPASS = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.CSUBJPASS",
    DEP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.DEP",
    DET = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.DET",
    DOBJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.DOBJ",
    EXPL = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.EXPL",
    INFMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.INFMOD",
    IOBJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.IOBJ",
    MARK = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.MARK",
    MEASURE = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.MEASURE",
    MWE = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.MWE",
    NEG = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.NEG",
    NN = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.NN",
    NPADVMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.NPADVMOD",
    NSUBJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.NSUBJ",
    NSUBJPASS = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.NSUBJPASS",
    NUM = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.NUM",
    NUMBER = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.NUMBER",
    PARATAXIS = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PARATAXIS",
    PARTMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PARTMOD",
    PCOMP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PCOMP",
    POBJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.POBJ",
    POSS = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.POSS",
    POSSESSIVE = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.POSSESSIVE",
    PRECONJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PRECONJ",
    PRED = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PRED",
    PREDET = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PREDET",
    PREP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PREP",
    PREPC = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PREPC",
    PRT = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PRT",
    PUNCT = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PUNCT",
    PURPCL = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.PURPCL",
    QUANTMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.QUANTMOD",
    RCMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.RCMOD",
    REF = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.REF",
    REL = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.REL",
    TMOD = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.TMOD",
    XCOMP = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.XCOMP",
    XSUBJ = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.XSUBJ",
}


---Process the response from the component.
---@param targetCas any JCas to write the results to
---@param results table the results from the component
function process_response(targetCas, results)
    ---Below follows basic DUUI deserialization logic, adapted from the regular duui-spacy component.

    local tokens, references = {}, {}

    for _, token in ipairs(results.tokens) do
        local token_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token", targetCas)
        token_anno:setBegin(token["begin"])
        token_anno:setEnd(token["end"])
        token_anno:addToIndexes()

        tokens[#tokens + 1] = token_anno
        references[#references + 1] = token_anno

        if token.lemma ~= nil then
            local lemma_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma", targetCas)
            lemma_anno:setBegin(token["begin"])
            lemma_anno:setEnd(token["end"])
            lemma_anno:setValue(token.lemma)
            token_anno:setLemma(lemma_anno)
            lemma_anno:addToIndexes()

            references[#references + 1] = lemma_anno
        end

        if token.pos_value ~= nil then
            local pos_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS", targetCas)
            pos_anno:setBegin(token["begin"])
            pos_anno:setEnd(token["end"])
            pos_anno:setPosValue(token.pos_value)
            pos_anno:setCoarseValue(token.pos_coarse)
            token_anno:setPos(pos_anno)
            pos_anno:addToIndexes()

            references[#references + 1] = pos_anno
        end

        if token.morph_value ~= nil and token.morph_value ~= "" then
            local morph_anno = luajava.newInstance(
                "de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.morph.MorphologicalFeatures", targetCas
            )
            morph_anno:setBegin(token["begin"])
            morph_anno:setEnd(token["end"])
            morph_anno:setValue(token.morph_value)
            token_anno:setMorph(morph_anno)
            morph_anno:addToIndexes()

            references[#references + 1] = morph_anno

            -- Add detailed infos, if available
            if token.morph_features.Gender ~= nil then
                morph_anno:setGender(token.morph_features.Gender)
            end
            if token.morph_features.Number ~= nil then
                morph_anno:setNumber(token.morph_features.Number)
            end
            if token.morph_features.Case ~= nil then
                morph_anno:setCase(token.morph_features.Case)
            end
            if token.morph_features.Degree ~= nil then
                morph_anno:setDegree(token.morph_features.Degree)
            end
            if token.morph_features.VerbForm ~= nil then
                morph_anno:setVerbForm(token.morph_features.VerbForm)
            end
            if token.morph_features.Tense ~= nil then
                morph_anno:setTense(token.morph_features.Tense)
            end
            if token.morph_features.Mood ~= nil then
                morph_anno:setMood(token.morph_features.Mood)
            end
            if token.morph_features.Voice ~= nil then
                morph_anno:setVoice(token.morph_features.Voice)
            end
            if token.morph_features.Definiteness ~= nil then
                morph_anno:setDefiniteness(token.morph_features.Definiteness)
            end
            if token.morph_features.Person ~= nil then
                morph_anno:setPerson(token.morph_features.Person)
            end
            if token.morph_features.Aspect ~= nil then
                morph_anno:setAspect(token.morph_features.Aspect)
            end
            if token.morph_features.Animacy ~= nil then
                morph_anno:setAnimacy(token.morph_features.Animacy)
            end
            if token.morph_features.Negative ~= nil then
                morph_anno:setNegative(token.morph_features.Negative)
            end
            if token.morph_features.NumType ~= nil then
                morph_anno:setNumType(token.morph_features.NumType)
            end
            if token.morph_features.Possessive ~= nil then
                morph_anno:setPossessive(token.morph_features.Possessive)
            end
            if token.morph_features.PronType ~= nil then
                morph_anno:setPronType(token.morph_features.PronType)
            end
            if token.morph_features.Reflex ~= nil then
                morph_anno:setReflex(token.morph_features.Reflex)
            end
            if token.morph_features.Transitivity ~= nil then
                morph_anno:setTransitivity(token.morph_features.Transitivity)
            end
        end
    end

    for _, dep in ipairs(results.dependencies) do
        local dep_type = dep.dependency_type
        local dep_anno_type = "de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.Dependency"

        local DEP_TYPE = string.upper(dep_type)
        dep_anno_type = DEP_TYPE_LOOKUP[DEP_TYPE] or dep_anno_type
        if string.upper(DEP_TYPE) == "ROOT" then
            dep_type = "--"
        end

        local dep_anno = luajava.newInstance(dep_anno_type, targetCas)
        dep_anno:setDependencyType(dep_type)

        dep_anno:setBegin(dep["begin"])
        dep_anno:setEnd(dep["end"])
        dep_anno:setFlavor(dep.flavor)

        local governor = tokens[dep.governor_index + 1]
        if governor ~= nil then
            dep_anno:setGovernor(governor)
        end

        local dependent = tokens[dep.dependent_index + 1]
        if dependent ~= nil then
            dep_anno:setDependent(dependent)
        end

        if governor ~= nil and dependent ~= nil then
            dependent:setParent(governor)
        end
        dep_anno:addToIndexes()

        references[#references + 1] = dep_anno
    end

    for _, entity in ipairs(results.entities) do
        local entity_anno

        local entity_value = entity.value
        local ENTITY_VALUE = string.upper(entity_value)
        if entity_value == "Organization" or ENTITY_VALUE == "ORG" then
            entity_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.ner.type.Organization", targetCas)
        elseif entity_value == "Person" or ENTITY_VALUE == "PER" then
            entity_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.ner.type.Person", targetCas)
        elseif entity_value == "Location" or ENTITY_VALUE == "LOC" then
            entity_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.ner.type.Location", targetCas)
        else
            entity_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.ner.type.NamedEntity", targetCas)
        end

        entity_anno:setBegin(entity["begin"])
        entity_anno:setEnd(entity["end"])
        entity_anno:setValue(entity_value)
        entity_anno:addToIndexes()

        references[#references + 1] = entity_anno
    end

    return references
end

function process_eos(targetCas, response)
    if response:statusCode() ~= 200 then
        error("Error " .. response:statusCode() .. " in communication with component: " .. response:body())
    end

    local results = json.decode(response:bodyUtf8())

    local references = {}
    for _, sentence in ipairs(results.sentences) do
        local sentence_anno = luajava.newInstance("de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence",
            targetCas)
        sentence_anno:setBegin(sentence["begin"])
        sentence_anno:setEnd(sentence["end"])
        sentence_anno:addToIndexes()

        references[#references + 1] = sentence_anno
    end

    add_annotator_metadata(targetCas, results.metadata, references)
end

---Add a SpacyAnnotatorMetaData annotation to the targetCas.
---@param targetCas any the JCas to add the annotation to
---@param metadata table<string, any> a table with metadata information
---@param references table<integer, any> a table of references to the annotations
function add_annotator_metadata(targetCas, metadata, references)
    local reference_array = luajava.newInstance("org.apache.uima.jcas.cas.FSArray", targetCas, #references)
    for i, ref in ipairs(references) do
        reference_array:set(i - 1, ref)
    end

    local annotation = luajava.newInstance("org.texttechnologylab.annotation.SpacyAnnotatorMetaData", targetCas)
    annotation:setReference(reference_array)
    annotation:setName(metadata.name)
    annotation:setVersion(metadata.version)
    annotation:setSpacyVersion(metadata.spacy_version)
    annotation:setModelName(metadata.model_name)
    annotation:setModelVersion(metadata.model_version)
    annotation:setModelLang(metadata.model_lang)
    annotation:setModelSpacyVersion(metadata.model_spacy_version)
    annotation:setModelSpacyGitVersion(metadata.model_spacy_git_version)
    annotation:addToIndexes()
end
