package org.hucompute.textimager.uima.stanza;

import de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS;
import de.tudarmstadt.ukp.dkpro.core.api.ner.type.NamedEntity;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma;
import de.tudarmstadt.ukp.dkpro.core.api.syntax.type.dependency.Dependency;
import org.apache.uima.UIMAException;
import org.apache.uima.cas.impl.XmiCasSerializer;
import org.apache.uima.fit.factory.JCasFactory;
import org.apache.uima.fit.util.JCasUtil;
import org.apache.uima.jcas.JCas;
import org.apache.uima.util.XMLSerializer;
import org.apache.uima.util.XmlCasSerializer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.texttechnologylab.DockerUnifiedUIMAInterface.DUUIComposer;
import org.texttechnologylab.DockerUnifiedUIMAInterface.driver.DUUIRemoteDriver;
import org.texttechnologylab.DockerUnifiedUIMAInterface.lua.DUUILuaContext;
import org.xml.sax.SAXException;

import javax.xml.transform.OutputKeys;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.URISyntaxException;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;

public class TestStanza {
    static DUUIComposer composer;
    static JCas cas;

    @BeforeAll
    static void beforeAll() throws URISyntaxException, IOException, UIMAException, SAXException {
        composer = new DUUIComposer()
                .withSkipVerification(true)
                .withLuaContext(new DUUILuaContext().withJsonLibrary());

        composer.addDriver(new DUUIRemoteDriver(100));
        cas = JCasFactory.createJCas();
    }

    @AfterAll
    static void afterAll() throws UnknownHostException {
        composer.shutdown();
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
    public void testStanzaDepFr() throws Exception {
        composer.add(
                new DUUIRemoteDriver.Component("http://localhost:9714"));

        String text = "Nous avons atteint la fin du sentier.";
        cas.setDocumentText(text);
        cas.setDocumentLanguage("fr");

        Sentence sentence = new Sentence(cas, 0, text.length());
        sentence.addToIndexes();

        composer.run(cas);

        // Should result in:
        // id: 1   word: Nous      head id: 3      head: atteint   deprel: nsubj
        // id: 2   word: avons     head id: 3      head: atteint   deprel: aux:tense
        // id: 3   word: atteint   head id: 0      head: root      deprel: root
        // id: 4   word: la        head id: 5      head: fin       deprel: det
        // id: 5   word: fin       head id: 3      head: atteint   deprel: obj
        // id: 6   word: de        head id: 8      head: sentier   deprel: case
        // id: 7   word: le        head id: 8      head: sentier   deprel: det
        // id: 8   word: sentier   head id: 5      head: fin       deprel: nmod
        // id: 9   word: .         head id: 3      head: atteint   deprel: punct

        String[] tokens = new String[] {
            "Nous",
            "avons",
            "atteint",
            "la",
            "fin",
            "de",
            "le",
            "sentier",
            "."
        };
        String[] casTokens = JCasUtil.select(cas, Token.class)
                .stream()
                .map(Token::getCoveredText)
                .toArray(String[]::new);
        
        assertArrayEquals(tokens, casTokens);

        String[] deps = new String[] {
            "nsubj", 
            "aux:tense", 
            "--", // root
            "det", 
            "obj", 
            "case", 
            "det", 
            "nmod", 
            "punct"
        };
        String[] casDeps = JCasUtil.select(cas, Dependency.class)
                .stream()
                .map(Dependency::getDependencyType)
                .toArray(String[]::new);

        assertArrayEquals(deps, casDeps);
    }

    @Test
    public void testStanzaLemmaEn() throws Exception {
        composer.add(
                new DUUIRemoteDriver.Component("http://localhost:9714"));

        String text = "Barack Obama was born in Hawaii.";
        cas.setDocumentText(text);
        cas.setDocumentLanguage("en");

        Sentence sentence = new Sentence(cas, 0, text.length());
        sentence.addToIndexes();

        composer.run(cas);

        // Should result in:
        // word: Barack    lemma: Barack
        // word: Obama     lemma: Obama
        // word: was       lemma: be
        // word: born      lemma: bear
        // word: in        lemma: in
        // word: Hawaii    lemma: Hawaii
        // word: .         lemma: .

        String[] tokens = new String[] {
            "Barack",
            "Obama",
            "was",
            "born",
            "in",
            "Hawaii",
            "."
        };
        String[] casTokens = JCasUtil.select(cas, Token.class)
                .stream()
                .map(Token::getCoveredText)
                .toArray(String[]::new);
        
        assertArrayEquals(tokens, casTokens);

        String[] lemmata = new String[] {
            "Barack",
            "Obama",
            "be",
            "bear",
            "in",
            "Hawaii",
            "."
        };
        String[] casLemmata = JCasUtil.select(cas, Lemma.class)
                .stream()
                .map(Lemma::getValue)
                .toArray(String[]::new);
        
        assertArrayEquals(lemmata, casLemmata);
    }
}