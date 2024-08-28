package org.hucompute.textimager.uima;

import org.apache.commons.compress.compressors.CompressorException;

import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token;
import de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.Dependency;

import org.apache.uima.UIMAException;
import org.apache.uima.fit.factory.JCasFactory;
import org.apache.uima.jcas.JCas;
import org.apache.uima.fit.util.JCasUtil;
import org.apache.uima.util.XmlCasSerializer;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;

import org.texttechnologylab.DockerUnifiedUIMAInterface.DUUIComposer;
import org.texttechnologylab.DockerUnifiedUIMAInterface.driver.DUUIRemoteDriver;
import org.texttechnologylab.DockerUnifiedUIMAInterface.driver.DUUIDockerDriver;
import org.texttechnologylab.DockerUnifiedUIMAInterface.lua.DUUILuaContext;

import org.xml.sax.SAXException;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URISyntaxException;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Objects;

public class CRF2oTest {
    static DUUIComposer composer;
    static JCas cas;

    @BeforeAll
    static void beforeAll() throws CompressorException, URISyntaxException, IOException, UIMAException, SAXException {
        composer = new DUUIComposer()
                .withSkipVerification(true)
                .withLuaContext(new DUUILuaContext().withJsonLibrary());

        composer.addDriver(new DUUIRemoteDriver(1000));
        composer.add(
                new DUUIRemoteDriver.Component("http://localhost:9714"));
        
        // composer.addDriver(new DUUIDockerDriver().withTimeout(10000));
        // composer.add(
        //         new DUUIDockerDriver.Component("duui-slc-crf2o/cu124:0.0.1"));

        cas = JCasFactory.createJCas();

        System.out.println("before All ...........");
    }

    @AfterAll
    static void afterAll() throws UnknownHostException {
        composer.shutdown();
        System.out.println("after All ...........");
    }

    @AfterEach
    public void afterEach() throws IOException, SAXException {
        composer.resetPipeline();

        ByteArrayOutputStream stream = new ByteArrayOutputStream();
        XmlCasSerializer.serialize(cas.getCas(), null, stream);
        System.out.println(stream.toString(StandardCharsets.UTF_8));
        cas.reset();
    }

    @Test
    public void dependencyParsingCRF2oTestEn() throws Exception {
        System.out.println("dependencyParsingCRF2oTestEn");

        String [] sentences = {
                "You should always try to avoid long sentences.",
                "Below are two examples, as well as some facts about long sentences in general.",
                "In 2005, Halton Borough Council put up a notice to tell the public about its plans to move a path from one place to another.",
                "Quite astonishingly, the notice was a 630 word sentence, which picked up one of our Golden Bull awards that year.",
                "Here is it in full."
        };
        String text =  String.join(" ", sentences);

        cas.setDocumentText(text);
        cas.setDocumentLanguage("en");

        int offset = 0;
        for (String sen : sentences) {
            int len = sen.length();
            Sentence sentence = new Sentence(cas, offset, offset + len);
            sentence.addToIndexes(cas);
            offset += len + 1;
        }

        composer.run(cas);

        String[] casTokens = JCasUtil.select(cas, Token.class)
                .stream()
                .map(t -> Objects.isNull(t.getForm()) ? t.getCoveredText() : t.getForm().getValue())
                .toArray(String[]::new);

        String[] tokens = {
                "You", "should", "always", "try", "to", "avoid", "long", "sentences", ".",
                "Below", "are", "two", "examples", ",", "as", "well", "as", "some", "facts",
                "about", "long", "sentences", "in", "general", ".", "In", "2005", ",",
                "Halton", "Borough", "Council", "put", "up", "a", "notice", "to", "tell",
                "the", "public", "about", "its", "plans", "to", "move", "a", "path",
                "from", "one", "place", "to", "another", ".", "Quite", "astonishingly", ",",
                "the", "notice", "was", "a", "630", "word", "sentence", ",", "which",
                "picked", "up", "one", "of", "our", "Golden", "Bull", "awards", "that",
                "year", ".", "Here", "is", "it", "in", "full", "."
        };
        assertArrayEquals(tokens, casTokens);

        String[] casDepTypes = JCasUtil.select(cas, Dependency.class)
                .stream()
                .map(Dependency::getDependencyType)
                .toArray(String[]::new);
        String[] depTypes = {
                "nsubj", "aux", "advmod", "--", "mark", "xcomp", "amod", "obj", "punct",
                "advmod", "--", "nummod", "nsubj", "punct", "case", "fixed", "fixed", "det",
                "conj", "case", "amod", "nmod", "case", "nmod", "punct", "case", "obl",
                "punct", "compound", "compound", "nsubj", "--", "compound:prt", "det", "obj",
                "mark", "acl", "det", "obj", "case", "nmod:poss", "obl", "mark", "advcl",
                "det", "obj", "case", "nummod", "obl", "case", "obl", "punct", "advmod",
                "advmod", "punct", "det", "nsubj", "cop", "det", "nummod", "compound", "--",
                "punct", "nsubj", "acl:relcl", "compound:prt", "obj", "case", "nmod:poss",
                "amod", "compound", "nmod", "det", "nmod", "punct", "--", "cop", "nsubj",
                "case", "advcl", "punct"
        };
        assertArrayEquals(depTypes, casDepTypes);

        int[] casDepBegins = JCasUtil.select(cas, Dependency.class)
                .stream()
                .mapToInt(Dependency::getBegin)
                .toArray();

        int[] depBegins = {
                0, 4, 11, 18, 22, 25, 31, 36, 45,
                47, 53, 57, 61, 69, 71, 74, 79, 82,
                87, 93, 99, 104, 114, 117, 124, 126, 129,
                133, 135, 142, 150, 158, 162, 165, 167, 174,
                177, 182, 186, 193, 199, 203, 209, 212, 217,
                219, 224, 229, 233, 239, 242, 249, 251, 257,
                270, 272, 276, 283, 287, 289, 293, 298, 306,
                308, 314, 321, 324, 328, 331, 335, 342, 347,
                354, 359, 363, 365, 370, 373, 376, 379, 383
        };
            

        assertArrayEquals(depBegins, casDepBegins);

        int[] casDepsEnds = JCasUtil.select(cas, Dependency.class)
                .stream()
                .mapToInt(Dependency::getEnd)
                .toArray();

        int[] depEnds = {
                3, 10, 17, 21, 24, 30, 35, 45, 46,
                52, 56, 60, 69, 70, 73, 78, 81, 86,
                92, 98, 103, 113, 116, 124, 125, 128, 133,
                134, 141, 149, 157, 161, 164, 166, 173, 176,
                181, 185, 192, 198, 202, 208, 211, 216, 218,
                223, 228, 232, 238, 241, 249, 250, 256, 270,
                271, 275, 282, 286, 288, 292, 297, 306, 307,
                313, 320, 323, 327, 330, 334, 341, 346, 353,
                358, 363, 364, 369, 372, 375, 378, 383, 384
        };
            
        assertArrayEquals(depEnds, casDepsEnds);

        System.out.println("Test dependencyParsingCRF2oTestEn Passed!");

    }
}
