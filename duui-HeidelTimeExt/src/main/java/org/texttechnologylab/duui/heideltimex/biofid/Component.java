package org.texttechnologylab.duui.heideltimex.biofid;

import static org.apache.uima.fit.factory.AnalysisEngineFactory.createEngineDescription;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence;
import de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token;
import de.unihd.dbs.uima.types.heideltime.Timex3;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.net.InetSocketAddress;
import java.nio.charset.Charset;
import java.util.Arrays;
import java.util.Iterator;
import org.apache.uima.UIMAException;
import org.apache.uima.analysis_engine.AnalysisEngine;
import org.apache.uima.cas.impl.XmiCasDeserializer;
import org.apache.uima.cas.impl.XmiCasSerializer;
import org.apache.uima.cas.impl.XmiSerializationSharedData;
import org.apache.uima.fit.factory.AggregateBuilder;
import org.apache.uima.fit.factory.JCasFactory;
import org.apache.uima.fit.factory.TypeSystemDescriptionFactory;
import org.apache.uima.fit.pipeline.SimplePipeline;
import org.apache.uima.fit.util.JCasUtil;
import org.apache.uima.jcas.JCas;
import org.apache.uima.resource.metadata.TypeSystemDescription;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.texttechnologylab.annotation.type.Time;
import org.texttechnologylab.heideltime.HeidelTimeX;
import org.xml.sax.SAXException;

public class Component implements AutoCloseable {

    private static final Logger logger = LoggerFactory.getLogger(Component.class);
    private static HttpServer server;

    public static void main(String[] args) throws Exception {
        int port = 9714;
        int workers = -1;
        Iterator<String> argsIterator = Arrays.asList(args).iterator();
        while (argsIterator.hasNext()) {
            String key = argsIterator.next().strip();
            int value;
            if (key.contains("=")) {
                value = Integer.parseInt(key.substring(key.indexOf("=") + 1));
                key = key.substring(0, key.indexOf("="));
            } else {
                value = Integer.parseInt(argsIterator.next());
            }
            switch (key) {
                case "-p":
                case "--port":
                    port = value;
                    break;
                case "-j":
                case "--workers":
                    workers = value;
                    break;
                default:
                    throw new IllegalArgumentException("Unknown option: " + key);
            }
        }
        server = startSever(port, workers);
    }

    public static HttpServer startSever(int port, int workers) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/v1/communication_layer", new CommunicationLayer());
        server.createContext("/v1/typesystem", new TypesystemHandler());
        server.createContext("/v1/process", new ProcessHandler());
        server.createContext("/v1/details/input_output", new IOHandler());

        if (workers == 1) {
            server.setExecutor(java.util.concurrent.Executors.newSingleThreadExecutor());
        } else if (workers > 0) {
            server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(workers));
        } else {
            server.setExecutor(java.util.concurrent.Executors.newCachedThreadPool());
        }
        server.start();
        logger.info("Started HeidelTimeX Server with Executor: {}", server.getExecutor().toString());
        return server;
    }

    @Override
    public void close() throws Exception {
        if (server != null) {
            logger.info("Shutting Down HeidelTimeX Server");
            server.stop(0);
        }
    }

    static class ProcessHandler implements HttpHandler {

        private final JCas jCas;
        private final AnalysisEngine analysisEngine;

        public ProcessHandler() {
            try {
                jCas = JCasFactory.createJCas();

                AggregateBuilder pipeline = new AggregateBuilder();
                pipeline.add(createEngineDescription(HeidelTimeX.class));
                analysisEngine = pipeline.createAggregate();
            } catch (UIMAException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public void handle(HttpExchange t) throws IOException {
            try {
                String contentLength = t.getRequestHeaders().getFirst("Content-Length");
                logger.info("Processing Request (size={})", contentLength);
                jCas.reset();
                XmiSerializationSharedData sharedData = new XmiSerializationSharedData();
                XmiCasDeserializer.deserialize(t.getRequestBody(), jCas.getCas(), true, sharedData);

                SimplePipeline.runPipeline(jCas, analysisEngine);

                for (Timex3 timex3 : JCasUtil.select(jCas, Timex3.class)) {
                    Time nTime = new Time(jCas);
                    nTime.setBegin(timex3.getBegin());
                    nTime.setEnd(timex3.getEnd());
                    nTime.setValue(timex3.getTimexType());
                    nTime.setIdentifier(timex3.getTimexValue());
                    nTime.addToIndexes();
                }

                t.sendResponseHeaders(200, 0);
                XmiCasSerializer.serialize(jCas.getCas(), null, t.getResponseBody(), false, sharedData);
            } catch (SAXException | IOException e) {
                logger.error(e.getMessage(), e);

                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                String message = e.getMessage() + ":\n" + sw;
                t.sendResponseHeaders(422, message.length()); // 422: Unprocessable Content
                t.getResponseBody().write(message.getBytes(Charset.defaultCharset()));
            } catch (Exception e) {
                logger.error(e.getMessage(), e);

                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                String message = e.getMessage() + ":\n" + sw;
                t.sendResponseHeaders(500, message.length());
                t.getResponseBody().write(message.getBytes(Charset.defaultCharset()));
            } finally {
                t.getResponseBody().close();
            }
        }
    }

    static class TypesystemHandler implements HttpHandler {

        @Override
        public void handle(HttpExchange t) throws IOException {
            try {
                TypeSystemDescription desc = TypeSystemDescriptionFactory.createTypeSystemDescription();
                StringWriter writer = new StringWriter();
                desc.toXML(writer);
                String response = writer.getBuffer().toString();

                t.sendResponseHeaders(200, response.getBytes(Charset.defaultCharset()).length);

                t.getResponseBody().write(response.getBytes(Charset.defaultCharset()));
            } catch (Exception e) {
                logger.error(e.getMessage(), e);

                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                String message = e.getMessage() + ":\n" + sw;
                t.sendResponseHeaders(500, message.length());
                t.getResponseBody().write(message.getBytes(Charset.defaultCharset()));
            } finally {
                t.getResponseBody().close();
            }
        }
    }

    static class IOHandler implements HttpHandler {

        @Override
        public void handle(HttpExchange t) throws IOException {
            try {
                JSONObject rObject = new JSONObject();
                rObject.put("input", new JSONArray().put(Token.class.getName()).put(Sentence.class.getName()));
                rObject.put("output", new JSONArray().put(Timex3.class.getName()).put(Time.class.getName()));
                String response = rObject.toString();
                t.sendResponseHeaders(200, response.getBytes(Charset.defaultCharset()).length);

                OutputStream os = t.getResponseBody();
                os.write(response.getBytes(Charset.defaultCharset()));
            } catch (Exception e) {
                logger.error(e.getMessage(), e);

                String message = e.getMessage();
                t.sendResponseHeaders(500, message.length());
                t.getResponseBody().write(message.getBytes(Charset.defaultCharset()));
            } finally {
                t.getResponseBody().close();
            }
        }
    }

    static class CommunicationLayer implements HttpHandler {

        @Override
        public void handle(HttpExchange t) throws IOException {
            String response =
                "serial = luajava.bindClass(\"org.apache.uima.cas.impl.XmiCasSerializer\")\n" +
                "deserial = luajava.bindClass(\"org.apache.uima.cas.impl.XmiCasDeserializer\")" +
                "function serialize(inputCas,outputStream,params)\n" +
                "  serial:serialize(inputCas:getCas(),outputStream)\n" +
                "end\n" +
                "\n" +
                "function deserialize(inputCas,inputStream)\n" +
                "  inputCas:reset()\n" +
                "  deserial:deserialize(inputStream,inputCas:getCas(),true)\n" +
                "end";
            t.sendResponseHeaders(200, response.length());
            OutputStream os = t.getResponseBody();
            os.write(response.getBytes());
            os.close();
        }
    }
}
