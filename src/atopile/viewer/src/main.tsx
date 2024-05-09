// @ts-nocheck
import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

import App from "./App";
// import OtherProviderFlow from "./AppOther";

const root = createRoot(document.getElementById("root"));
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
