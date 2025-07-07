package org.texttechnologylab.duui.heideltimex;

import com.sun.net.httpserver.HttpServer;
import de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS;
import de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS_NOUN;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token;
import de.unihd.dbs.uima.types.heideltime.Timex3;
import org.apache.uima.cas.CASException;
import org.apache.uima.cas.impl.XmiCasDeserializer;
import org.apache.uima.cas.impl.XmiCasSerializer;
import org.apache.uima.fit.factory.JCasFactory;
import org.apache.uima.fit.util.JCasUtil;
import org.apache.uima.jcas.JCas;
import org.apache.uima.jcas.tcas.Annotation;
import org.apache.uima.resource.ResourceInitializationException;
import org.assertj.core.api.Assertions;
import org.junit.jupiter.api.Test;
import org.texttechnologylab.duui.heideltimex.biofid.Component;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Collection;
import java.util.List;

public class TestHeidelTimeBIOfid {
    public static final List<String> timeMentions = List.of("Am 19.12.1984", "im Vorjahresmonat", "vom vorherigen Tag", "nächstes Jahr", "im Jahre 1985");


    public static JCas getJCas() throws ResourceInitializationException, CASException {
        JCas jCas = JCasFactory.createJCas();
        jCas.setDocumentText(String.join(" foo bar ", timeMentions));
        jCas.setDocumentLanguage("de");
        new Sentence(jCas, 0, jCas.getDocumentText().length()).addToIndexes();
        int offset = 0;
        for (String s : jCas.getDocumentText().split(" ")) {
            Token token = new Token(jCas, offset, offset + s.length());
            POS pos = new POS_NOUN(jCas, offset, offset + s.length());
            pos.setPosValue("NN");
            pos.addToIndexes();
            token.setPos(pos);
            token.addToIndexes();
            offset += s.length() + 1;
        }
        return jCas;
    }

    @Test
    public void testComponent() throws Exception {
        HttpServer server = Component.startSever(9714, 1);
        try {
            JCas jCas = getJCas();

            HttpClient client = HttpClient.newHttpClient();
            ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
            XmiCasSerializer.serialize(jCas.getCas(), byteArrayOutputStream);
            HttpRequest request = HttpRequest.newBuilder(new URI("http://localhost:9714/v1/process"))
                    .POST(HttpRequest.BodyPublishers.ofByteArray(byteArrayOutputStream.toByteArray()))
                    .build();
            HttpResponse<byte[]> httpResponse = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
            XmiCasDeserializer.deserialize(new ByteArrayInputStream(httpResponse.body()), jCas.getCas());

            Collection<Timex3> timex3s = JCasUtil.select(jCas, Timex3.class);
            Assertions.assertThat(timex3s).hasSize(timeMentions.size());

            printResults(timex3s);
        } finally {
            server.stop(0);
        }
    }

    public static void printResults(Collection<? extends Annotation> timex3s) {
        for (Annotation annotation : timex3s) {
            StringBuffer stringBuffer = new StringBuffer();
            annotation.prettyPrint(0, 2, stringBuffer, true);
            System.out.print(stringBuffer);
            System.out.println("\n  text: \"" + annotation.getCoveredText() + "\"\n");
        }
    }
}
