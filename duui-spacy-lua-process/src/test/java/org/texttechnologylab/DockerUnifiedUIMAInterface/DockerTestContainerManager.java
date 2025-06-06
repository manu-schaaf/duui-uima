package org.texttechnologylab.DockerUnifiedUIMAInterface;

import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.async.ResultCallback;
import com.github.dockerjava.api.command.CreateContainerResponse;
import com.github.dockerjava.api.model.ExposedPort;
import com.github.dockerjava.api.model.Frame;
import com.github.dockerjava.api.model.HostConfig;
import com.github.dockerjava.api.model.PortBinding;
import com.github.dockerjava.core.DockerClientBuilder;

import java.io.IOException;
import java.net.ServerSocket;
import java.util.UUID;

/**
 * Test helper class to create and run a container image for testing purposes.
 * Will search for a random free port
 */
public class DockerTestContainerManager implements AutoCloseable {
    final DockerClient dockerClient = DockerClientBuilder.getInstance().build();
    final CreateContainerResponse container;
    final int port = getFreePort();

    public DockerTestContainerManager(String imageName) {
        this(imageName, "test-duui-" + UUID.randomUUID(), 5000);
    }

    public DockerTestContainerManager(String imageName, String containerName) {
        this(imageName, containerName, 5000);
    }

    public DockerTestContainerManager(String imageName, long startupDelay) {
        this(imageName, "test-duui-" + UUID.randomUUID(), startupDelay);
    }

    public DockerTestContainerManager(String imageName, String containerName, long startupDelay) {
        System.out.printf("[DockerTestContainerManager] Creating Container Image for %s%n", imageName);
        container = dockerClient.createContainerCmd(imageName)
                .withHostConfig(
                        HostConfig.newHostConfig()
                                .withAutoRemove(true)
                                .withPublishAllPorts(true)
                                .withPortBindings(PortBinding.parse("%d:9714".formatted(port)))
                )
                .withExposedPorts(ExposedPort.tcp(9714))
                .withName(containerName)
                .exec();
        String containerId = container.getId();
        System.out.printf("[DockerTestContainerManager] Container Image Created: %s%n", containerId);
        System.out.printf("[DockerTestContainerManager] Starting Container as %s with port binding %d:9714%n", containerName, port);
        dockerClient.attachContainerCmd(containerId)
                .withStdErr(true)
                .withStdOut(true)
                .withFollowStream(true)
                .exec(new ResultCallback.Adapter<Frame>() {
                    public void onNext(Frame object) {
                        String message = new String(object.getPayload());
                        for (String line : message.split("\r?\n")) {
                            System.out.printf("[DockerTestContainer:%s] %s%n", containerId.substring(0, 10), line);
                        }
                    }
                });
        dockerClient.startContainerCmd(containerId).exec();

        try {
            System.out.printf("[DockerTestContainerManager] Waiting %dms for Container to Come Online%n", startupDelay);
            Thread.sleep(startupDelay);
        } catch (InterruptedException e) {
        }

        System.out.println("[DockerTestContainerManager] Container Started: " + containerId);
    }

    private static int getFreePort() {
        try (ServerSocket socket = new ServerSocket(0)) {
            return socket.getLocalPort();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public int getPort() {
        return port;
    }

    @Override
    public void close() throws Exception {
        System.out.println("[DockerTestContainerManager] Stopping Container: " + container.getId());
        dockerClient.stopContainerCmd(container.getId()).withTimeout(10).exec();
        System.out.println("[DockerTestContainerManager] Container Stopped");
        System.out.println("[DockerTestContainerManager] Stopping Docker Client");
        dockerClient.close();
    }

}