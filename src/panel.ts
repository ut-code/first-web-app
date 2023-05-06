import * as vscode from "vscode";
import convertMarkdownToHtml from "./utils/convertMarkdownToHtml";

const panel = vscode.window.createWebviewPanel(
  "first-web-game-maker",
  "First Web Game Maker",
  vscode.ViewColumn.Two,
  {
    enableScripts: true,
  }
);

// panel.webview.html = convertMarkdownToHtml(
//   "./contents/descriptions/htmlDescription.md"
// );

panel.webview.html = convertMarkdownToHtml(
  "./contents/descriptions/pacmanDescription.md"
);

export default panel;
