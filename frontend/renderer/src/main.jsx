import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App.jsx"
import "./index.css"

// When running in a browser (not Electron), install the browser API shim.
// In Electron, preload.js sets window.api via contextBridge before this runs.
function boot() {
  ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}

if (!window.api) {
  import("./api.js").then(({ api }) => {
    window.api = api
    boot()
  })
} else {
  boot()
}