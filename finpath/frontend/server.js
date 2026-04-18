const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");
const cors = require("cors");
const path = require("path");

const app = express();

app.use(cors());
app.use(express.static(path.join(__dirname, "public")));

app.use(
  "/api",
  createProxyMiddleware({
    target: "http://localhost:8000",
    changeOrigin: true,
    pathRewrite: { "^/api": "" },
    on: {
      proxyReq: (_proxyReq, req) => {
        console.log(`[PROXY] ${req.method} ${req.url} -> :8000`);
      },
      error: (err, req) => {
        console.error(`[PROXY_ERROR] ${req.method} ${req.url}: ${err.message}`);
      },
    },
  })
);

app.get(/.*/, (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.listen(3000, () => {
  console.log("FinPath Frontend running on http://localhost:3000");
});
