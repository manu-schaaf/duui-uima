-- Bind static classes from java
StandardCharsets = luajava.bindClass("java.nio.charset.StandardCharsets")
JCasUtil = luajava.bindClass("org.apache.uima.fit.util.JCasUtil")

---Indicates that this component supports the "new" `process` method.
SUPPORTS_PROCESS = true
---Indicates that this component does NOT support the old `serialize`/`deserialize` methods.
SUPPORTS_SERIALIZE = false

---Create and yield batches of elements from an iterator after applying a transform function.
---@param iterator any an iterator over annotations
---@param batch_size integer size of each batch sent to the component
function get_batches(iterator, batch_size)
    local entities, references = {}, {}
    while iterator:hasNext() do
        local entity = iterator:next()

        references[#references + 1] = entity
        entities[#entities + 1] = {
            reference = tostring(#references),
            text = entity:getCoveredText()
        }

        if #entities == batch_size then
            coroutine.yield({
                entities, references
            })
            entities, references = {}, {}
        end
    end

    if #entities > 0 then
        coroutine.yield({
            entities, references
        })
    end
end

---Iterate over batches of elements from an iterator after applying a transform function.
---@param iterator any an iterator over annotations
---@param batch_size integer size of each batch
---@return fun(): table an iterator over batches to process
function batched(iterator, batch_size)
    local co = coroutine.create(function() get_batches(iterator, batch_size) end)
    return function()
        local _, batch = coroutine.resume(co)
        return batch
    end
end

REQUEST_BATCH_SIZE = 4096
ANNOTATION_TYPE = "de.tudarmstadt.ukp.dkpro.core.api.ner.type.Location"

---Process the sentences in the given JCas in small batches.
---@param sourceCas any JCas (view) to process
---@param handler any DuuiHttpRequestHandler with a connection to the running component
---@param parameters table optional parameters
---@param targetCas any JCas (view) to write the results to (optional)
function process(sourceCas, handler, parameters, targetCas)
    parameters = parameters or {}

    local batch_size = parameters.request_batch_size or REQUEST_BATCH_SIZE
    local annotation_type = parameters.annotation_type or ANNOTATION_TYPE

    local query = {
        mode = parameters.mode or "find",
        result_selection = parameters.result_selection or "first",
    }

    ---parameters.filter should be a table with keys (any of), each holding a single string: feature_class, feature_code, country_code
    if parameters.filter ~= nil then
        query.filter = parameters.filter
    end

    if query.mode ~= "find" and parameters.max_dist ~= nil then
        query.max_dist = tostring(parameters.max_dist)
    end

    if query.mode == "levenshtein" and parameters.state_limit ~= nil then
        query.state_limit = tostring(parameters.state_limit)
    end

    handler:setHeader("Content-Type", "application/json")

    local results, modification = {}, nil
    local iterator = JCasUtil:select(sourceCas, luajava.bindClass(annotation_type)):iterator()
    for batch in batched(iterator, batch_size) do
        local entities, references = table.unpack(batch)
        query.queries = entities

        local response = handler:process(json.encode(query))

        if not response:ok() then
            error("Error " .. response:statusCode() .. " in communication with component: " .. response:bodyAsString())
        end

        results = json.decode(response:body())
        process_response(targetCas, results, references)
        modification = results.modification or modification
    end

    if modification ~= nil then
        local document_modification = luajava.newInstance("org.texttechnologylab.annotation.DocumentModification", targetCas)
        document_modification:setUser(modification.user)
        document_modification:setTimestamp(modification.timestamp)
        document_modification:setComment(modification.comment)
        document_modification:addToIndexes()
    end
end

---Process the response from the component.
---@param targetCas any JCas
---@param results table the results from the component
---@param references table<integer, any>
function process_response(targetCas, results, references)
    for _, entity in ipairs(results.results) do
        local gn = entity.entry

        local annotation = luajava.newInstance("org.texttechnologylab.annotation.geonames.GeoNamesEntity", targetCas)
        annotation:setId(tonumber(gn.id))
        annotation:setName(gn.name)
        annotation:setLatitude(gn.latitude)
        annotation:setLongitude(gn.longitude)
        -- Feature Class & Feature Code are enum strings and will cause an error if set to an empty string
        if gn.feature_class ~= nil and gn.feature_class ~= "" then
            annotation:setFeatureClass(gn.feature_class)
        end
        if gn.feature_code ~= nil and gn.feature_code ~= "" then
            annotation:setFeatureCode(gn.feature_code)
        end
        annotation:setCountryCode(gn.country_code)
        annotation:setAdm1(gn.adm1)
        annotation:setAdm2(gn.adm2)
        annotation:setAdm3(gn.adm3)
        annotation:setAdm4(gn.adm4)

        if gn.elevation ~= nil then
            annotation:setElevation(gn.elevation)
        end

        local reference = references[tonumber(entity.reference)]
        if reference == nil then
            error("Failed to resolve reference annotation with index " .. entity.reference)
        else
            annotation:setReferenceAnnotation(reference)
            annotation:setBegin(reference:getBegin())
            annotation:setEnd(reference:getEnd())
        end

        annotation:addToIndexes()
    end
end
