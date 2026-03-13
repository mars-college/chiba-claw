import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import http from "node:http";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const disabledEnvFile = path.join(repoRoot, ".env.test.skip");
const executeScript = path.join(
  repoRoot,
  "skills",
  "eden-tools",
  "scripts",
  "execute-tool.sh"
);
const listScript = path.join(
  repoRoot,
  "skills",
  "eden-tools",
  "scripts",
  "list-tools.sh"
);

function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      ...options,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("close", (code, signal) => {
      resolve({ code, signal, stdout, stderr });
    });
  });
}

async function startMockEdenServer() {
  const state = {
    executeBodies: [],
    executeHeaders: [],
    listHeaders: [],
    taskPolls: 0,
  };

  const server = http.createServer(async (request, response) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    const bodyChunks = [];
    for await (const chunk of request) {
      bodyChunks.push(Buffer.from(chunk));
    }
    const bodyText = Buffer.concat(bodyChunks).toString("utf8");
    const body = bodyText ? JSON.parse(bodyText) : null;

    const apiKeyHeader = request.headers["x-api-key"];
    const authHeader = request.headers.authorization;

    if (
      apiKeyHeader !== "edn_sk_test" ||
      authHeader !== "Bearer edn_sk_test"
    ) {
      response.writeHead(401, { "content-type": "application/json" });
      response.end(JSON.stringify({ error: "unauthorized" }));
      return;
    }

    if (request.method === "GET" && url.pathname === "/v1/tools") {
      state.listHeaders.push({
        "x-api-key": apiKeyHeader,
        authorization: authHeader,
      });
      response.writeHead(200, { "content-type": "application/json" });
      response.end(
        JSON.stringify({
          items: [
            { id: "fal/nano-banana", name: "Nano Banana" },
            { id: "eden/slow-tool", name: "Slow Tool" },
          ],
        })
      );
      return;
    }

    if (request.method === "POST" && url.pathname === "/v1/tools/fal/nano-banana/execute") {
      state.executeBodies.push(body);
      state.executeHeaders.push({
        "x-api-key": apiKeyHeader,
        authorization: authHeader,
      });
      response.writeHead(200, { "content-type": "application/json" });
      response.end(
        JSON.stringify({
          images: [{ url: "https://example.com/generated.png" }],
        })
      );
      return;
    }

    if (request.method === "POST" && url.pathname === "/v1/tools/eden/slow-tool/execute") {
      state.executeBodies.push(body);
      state.executeHeaders.push({
        "x-api-key": apiKeyHeader,
        authorization: authHeader,
      });
      response.writeHead(200, { "content-type": "application/json" });
      response.end(
        JSON.stringify({
          id: "tsk_123",
          status: "queued",
        })
      );
      return;
    }

    if (request.method === "GET" && url.pathname === "/v1/tasks/tsk_123") {
      state.taskPolls += 1;
      const payload =
        state.taskPolls < 3
          ? { id: "tsk_123", status: state.taskPolls === 1 ? "queued" : "running" }
          : {
              id: "tsk_123",
              status: "completed",
              output: {
                asset: {
                  url: "https://example.com/final.mp4",
                },
              },
            };
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify(payload));
      return;
    }

    response.writeHead(404, { "content-type": "application/json" });
    response.end(JSON.stringify({ error: "not_found" }));
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const baseUrl =
    typeof address === "object" && address ? `http://127.0.0.1:${address.port}` : "";

  return {
    baseUrl,
    state,
    close: async () => {
      await new Promise((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()));
      });
    },
  };
}

test("eden-tools lists tools and executes immediate responses", async () => {
  const mock = await startMockEdenServer();

  try {
    const listResult = await runCommand("bash", [listScript, "--limit", "2", "--compact"], {
      cwd: repoRoot,
      env: {
        ...process.env,
        CHIBA_CLAW_ENV_FILE: disabledEnvFile,
        EDEN_API_URL: mock.baseUrl,
        EDEN_API_KEY: "edn_sk_test",
      },
    });

    assert.equal(listResult.code, 0, listResult.stderr || listResult.stdout);
    const listPayload = JSON.parse(listResult.stdout);
    assert.equal(listPayload.items.length, 2);
    assert.deepEqual(mock.state.listHeaders[0], {
      "x-api-key": "edn_sk_test",
      authorization: "Bearer edn_sk_test",
    });

    const executeResult = await runCommand(
      "bash",
      [
        executeScript,
        "--tool-id",
        "fal/nano-banana",
        "--arg",
        "prompt=banana",
        "--arg",
        "num_images=2",
        "--compact",
      ],
      {
        cwd: repoRoot,
        env: {
          ...process.env,
          CHIBA_CLAW_ENV_FILE: disabledEnvFile,
          EDEN_API_URL: mock.baseUrl,
          EDEN_API_KEY: "edn_sk_test",
        },
      }
    );

    assert.equal(executeResult.code, 0, executeResult.stderr || executeResult.stdout);
    const payload = JSON.parse(executeResult.stdout);
    assert.equal(payload.images[0].url, "https://example.com/generated.png");
    assert.deepEqual(mock.state.executeBodies[0], { data: { prompt: "banana", num_images: 2 } });
    assert.deepEqual(mock.state.executeHeaders[0], {
      "x-api-key": "edn_sk_test",
      authorization: "Bearer edn_sk_test",
    });
  } finally {
    await mock.close();
  }
});

test("eden-tools polls task-like execute responses until completion", async () => {
  const mock = await startMockEdenServer();

  try {
    const executeResult = await runCommand(
      "bash",
      [
        executeScript,
        "--tool-id",
        "eden/slow-tool",
        "--arg",
        "prompt=wait for it",
        "--poll-interval",
        "0.01",
        "--timeout",
        "5",
        "--compact",
      ],
      {
        cwd: repoRoot,
        env: {
          ...process.env,
          CHIBA_CLAW_ENV_FILE: disabledEnvFile,
          EDEN_API_URL: mock.baseUrl,
          EDEN_API_KEY: "edn_sk_test",
        },
      }
    );

    assert.equal(executeResult.code, 0, executeResult.stderr || executeResult.stdout);
    const payload = JSON.parse(executeResult.stdout);
    assert.equal(payload.asset.url, "https://example.com/final.mp4");
    assert.equal(mock.state.taskPolls, 3);
    assert.deepEqual(mock.state.executeBodies[0], { data: { prompt: "wait for it" } });
    assert.deepEqual(mock.state.executeHeaders[0], {
      "x-api-key": "edn_sk_test",
      authorization: "Bearer edn_sk_test",
    });
  } finally {
    await mock.close();
  }
});
