import express from 'express';
import { spawn } from 'child_process';
import readline from 'readline';

const app = express();
app.use(express.json());

const command = process.argv.slice(2);
if (command.length === 0) {
  console.error("Usage: node proxy.js <command> [args...]");
  process.exit(1);
}

const child = spawn(command[0], command.slice(1), {
  env: process.env,
  stdio: ['pipe', 'pipe', 'inherit'] // connect stdin/stdout as pipes, map stderr to parent
});

let sseRes = null;

app.get('/sse', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });
  sseRes = res;
  
  // Instruct the MCP Client where to POST JSON-RPC payloads
  res.write(`event: endpoint\ndata: /message\n\n`);
  
  req.on('close', () => { sseRes = null; });
});

app.post('/message', (req, res) => {
  if (child.stdin) {
    child.stdin.write(JSON.stringify(req.body) + '\n');
  }
  res.sendStatus(202);
});

// Relay MCP Server's stdio output back to the connected SSE Client
const rl = readline.createInterface({ input: child.stdout });
rl.on('line', (line) => {
  if (sseRes) {
    sseRes.write(`event: message\ndata: ${line}\n\n`);
  }
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`SSE Proxy listening on 0.0.0.0:${PORT} wrapping command: ${command.join(' ')}`);
});
