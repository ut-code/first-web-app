import { type Command } from "./types/command";
import toCommands from "./utils/toCommands";
import insertHelloWorldAtTopCommand from "./contents/commands/insertHelloWorldAtTop";
import insertAtCursorCommand from "./contents/commands/insertAtCursor";
import deleteAfterCursorCommand from "./contents/commands/deleteAfterCursor";
import pacmanCommands from "./contents/commands/pacmanCommands";
import htmlCommands from "./contents/commands/htmlCommands";

const commands: Command[] = [
  insertHelloWorldAtTopCommand,
  insertAtCursorCommand,
  deleteAfterCursorCommand,
  ...pacmanCommands,
  ...htmlCommands,
];

export default toCommands(commands);
