package org.texttechnologylab.duui.heideltimex;

import de.unihd.dbs.uima.types.heideltime.Timex3;
import org.apache.uima.fit.util.JCasUtil;
import org.apache.uima.jcas.JCas;
import org.junit.jupiter.api.Test;
import org.texttechnologylab.DockerUnifiedUIMAInterface.DUUIComposer;
import org.texttechnologylab.DockerUnifiedUIMAInterface.driver.DUUIDockerDriver;
import org.texttechnologylab.DockerUnifiedUIMAInterface.lua.DUUILuaContext;

import static org.texttechnologylab.duui.heideltimex.TestHeidelTimeBIOfid.getJCas;
import static org.texttechnologylab.duui.heideltimex.TestHeidelTimeBIOfid.printResults;

/**
 * Requires VM args: --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.util/java.base=ALL-UNNAMED
 */
public class TestHeidelTimeDUUI {

    @Test
    public void testDuui() throws Exception {
        DUUIComposer composer = new DUUIComposer()
                .withLuaContext(new DUUILuaContext().withJsonLibrary())
                .withSkipVerification(true);

        composer.addDriver(new DUUIDockerDriver(10000));
        composer.add(new DUUIDockerDriver.Component("docker.texttechnologylab.org/duui-heideltimex:latest").build());

        JCas jCas = getJCas();
        composer.run(jCas);
        composer.shutdown();

        printResults(JCasUtil.select(jCas, Timex3.class));
    }
}
