package org.texttechnologylab.DockerUnifiedUIMAInterface;

import de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.morph.MorphologicalFeatures;
import de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS;
import de.tudarmstadt.ukp.dkpro.core.api.ner.type.NamedEntity;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token;
import org.apache.uima.cas.CASException;
import org.apache.uima.fit.factory.JCasFactory;
import org.apache.uima.fit.util.JCasUtil;
import org.apache.uima.jcas.JCas;
import org.apache.uima.resource.ResourceInitializationException;
import org.junit.jupiter.api.*;
import org.texttechnologylab.DockerUnifiedUIMAInterface.driver.DUUIRemoteDriver;
import org.texttechnologylab.DockerUnifiedUIMAInterface.lua.DUUILuaContext;
import org.texttechnologylab.annotation.SpacyAnnotatorMetaData;

import java.io.IOException;
import java.net.URISyntaxException;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public class TestSpacyBatched {
    DockerTestContainerManager container;

    @BeforeAll
    public void beforeAll() {
        container = new DockerTestContainerManager(
                "docker.texttechnologylab.org/duui-spacy-lua-process:0.2.2",
                8000
        );
    }

    @AfterAll
    public void afterAll() throws Exception {
        if (container != null) {
            container.close();
        }
    }

    static class ComposerManager implements AutoCloseable {
        public final DUUIComposer composer;
        public ComposerManager() throws Exception {
            composer = new DUUIComposer()
                    .withLuaContext(
                            new DUUILuaContext()
                                    .withJsonLibrary())
                    .withSkipVerification(true);
            composer.addDriver(new DUUIRemoteDriver(10000));
        }

        @Override
        public void close() throws Exception {
            composer.shutdown();
        }
    }

    private DUUIRemoteDriver.Component getComponent() throws URISyntaxException, IOException {
       return new DUUIRemoteDriver.Component("http://localhost:%d".formatted(container.getPort()));
    }

    private static JCas getJCas() throws ResourceInitializationException, CASException {
        JCas jCas = JCasFactory.createJCas();
        jCas.setDocumentText(
                "Die Goethe Universität ist auf vier große Universitätsgelände über das Frankfurter Stadtgebiet verteilt.\n "
                        + "Barack Obama war der 44. Präsident der Vereinigten Staaten von Amerika."
        );
        jCas.setDocumentLanguage("de");
        return jCas;
    }

    @Test
    public void test_sm_wo_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "sm")
                            .build()
            );

            JCas jCas = getJCas();

            composer.run(jCas, "spacy-lua-process-test/sm-wo-sents");
            composer.resetPipeline();

            printResult(jCas);
        }
    }

    @Test
    public void test_sm_w_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "sm")
                            .build()
            );

            JCas jCas = getJCas();
            new Sentence(jCas, 0, 104).addToIndexes();
            new Sentence(jCas, 106, 177).addToIndexes();

            composer.run(jCas, "spacy-lua-process-test/sm-w-sents");

            printResult(jCas);
        }
    }

    @Test
    public void test_md_wo_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "md")
                            .build()
            );

            JCas jCas = getJCas();

            composer.run(jCas, "spacy-lua-process-test/md-wo-sents");

            printResult(jCas);
        }
    }

    @Test
    public void test_md_w_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "md")
                            .build()
            );

            JCas jCas = getJCas();
            new Sentence(jCas, 0, 104).addToIndexes();
            new Sentence(jCas, 106, 177).addToIndexes();

            composer.run(jCas, "spacy-lua-process-test/md-w-sents");

            printResult(jCas);
        }
    }

    @Test
    public void test_lg_wo_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "lg")
                            .build()
            );

            JCas jCas = getJCas();

            composer.run(jCas, "spacy-lua-process-test/lg-wo-sents");

            printResult(jCas);
        }
    }

    @Test
    public void test_lg_w_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "lg")
                            .build()
            );

            JCas jCas = getJCas();
            new Sentence(jCas, 0, 104).addToIndexes();
            new Sentence(jCas, 106, 177).addToIndexes();

            composer.run(jCas, "spacy-lua-process-test/lg-w-sents");

            printResult(jCas);
        }
    }

    @Test
    public void test_trf_wo_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "trf")
                            .build()
            );

            JCas jCas = getJCas();

            composer.run(jCas, "spacy-lua-process-test/trf-wo-sents");
            composer.resetPipeline();

            printResult(jCas);
        }
    }

    @Test
    public void test_trf_w_sents() throws Exception {
        try (ComposerManager mngr = new ComposerManager()) {
            DUUIComposer composer = mngr.composer;
            composer.add(
                    getComponent()
                            .withParameter("spacy_model_size", "trf")
                            .build()
            );

            JCas jCas = getJCas();
            new Sentence(jCas, 0, 104).addToIndexes();
            new Sentence(jCas, 106, 177).addToIndexes();

            composer.run(jCas, "spacy-lua-process-test/trf");

            printResult(jCas);
        }
    }

    private static void printResult(JCas jCas) {
        System.out.println("### SpacyAnnotatorMetaData ###");
        for (SpacyAnnotatorMetaData annotation : JCasUtil.select(jCas, SpacyAnnotatorMetaData.class)) {
            System.out.println(annotation.toString(2));
            System.out.println();
        }

        System.out.println("### Sentence ###");
        for (Sentence annotation : JCasUtil.select(jCas, Sentence.class)) {
            System.out.println(annotation.toString(2));
            System.out.println();
        }

        System.out.println("### Token ###");
        for (Token annotation : JCasUtil.select(jCas, Token.class)) {
            System.out.println(annotation.toString(2));
            System.out.println();
        }

        System.out.println("### Lemma ###");
        for (Lemma annotation : JCasUtil.select(jCas, Lemma.class)) {
            System.out.println(annotation.toString(2));
            System.out.println();
        }

        System.out.println("### POS ###");
        for (POS annotation : JCasUtil.select(jCas, POS.class)) {
            System.out.println(annotation.toString(2));
            System.out.println();
        }

        System.out.println("### MorphologicalFeatures ###");
        for (MorphologicalFeatures annotation : JCasUtil.select(jCas, MorphologicalFeatures.class)) {
            System.out.println(annotation.toString(2));
            System.out.println();
        }

        System.out.println("### NamedEntity ###");
        for (NamedEntity annotation : JCasUtil.select(jCas, NamedEntity.class)) {
            System.out.print(annotation.toString(2));
            System.out.printf("%n  text: '%s'%n", annotation.getCoveredText());
            System.out.println();
        }
    }
}
