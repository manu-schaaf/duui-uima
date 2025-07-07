package org.texttechnologylab.duui.heideltimex;

import com.sun.net.httpserver.HttpServer;
import de.unihd.dbs.uima.types.heideltime.Timex3;
import org.apache.uima.cas.impl.XmiCasDeserializer;
import org.apache.uima.fit.factory.JCasFactory;
import org.apache.uima.fit.util.JCasUtil;
import org.apache.uima.jcas.JCas;
import org.junit.jupiter.api.Test;
import org.texttechnologylab.DockerUnifiedUIMAInterface.DUUIComposer;
import org.texttechnologylab.DockerUnifiedUIMAInterface.driver.DUUIDockerDriver;
import org.texttechnologylab.DockerUnifiedUIMAInterface.driver.DUUIRemoteDriver;
import org.texttechnologylab.DockerUnifiedUIMAInterface.lua.DUUILuaContext;
import org.texttechnologylab.duui.heideltimex.biofid.Component;

import java.io.File;
import java.io.FileInputStream;
import java.util.List;

import static org.texttechnologylab.duui.heideltimex.TestHeidelTimeBIOfid.printResults;

/**
 * Requires VM args: --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.util/java.base=ALL-UNNAMED
 */
public class TestHeidelTimeTweet {

    @Test
    public void test_tweet() throws Exception {
        HttpServer server = Component.startSever(9714, 1);
        try {
            DUUIComposer composer = new DUUIComposer()
                    .withLuaContext(new DUUILuaContext().withJsonLibrary())
                    .withSkipVerification(true);

            composer.addDriver(new DUUIDockerDriver(10000));
            composer.addDriver(new DUUIRemoteDriver(10000));

            composer.add(
                    new DUUIDockerDriver.Component("docker.texttechnologylab.org/duui-spacy-lua-process:latest")
//                    new DUUIRemoteDriver.Component("http://localhost:11001")
                            .withParameter("spacy_model_size", "sm")
                            .withName("duui-spacy")
                            .build()
            );
            composer.add(
                    new DUUIDockerDriver.Component("docker.texttechnologylab.org/duui-heideltimex:latest")
//                    new DUUIRemoteDriver.Component("http://localhost:9714")
                            .withName("duui-heideltimex")
                            .build()
            );

            for (String tweetFileName : List.of("xmi/1854075437380403232.xmi", "xmi/1854537200039252145.xmi")) {
                FileInputStream tweetFile = new FileInputStream(
                        new File(TestHeidelTimeTweet.class.getClassLoader().getResource(tweetFileName).toURI())
                );

                JCas jCas = JCasFactory.createJCas();
                XmiCasDeserializer.deserialize(tweetFile, jCas.getCas());

                composer.run(jCas);

                printResults(JCasUtil.select(jCas, Timex3.class));
            }
            composer.shutdown();
        } finally {
            server.stop(0);
        }
    }
}
