const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync("static/approval_flow.js", "utf8"), context);
const flow = context.window.GenmarApprovalFlow;

assert.strictEqual(flow.autoAdvanceAfterApproval, false);
assert.strictEqual(flow.afterApproval(), false);

let opened = null;
const state = { items: [10, 20, 30], index: 1, open: (id, index) => { opened = [id, index]; } };
assert.strictEqual(flow.next(state), 2);
assert.deepStrictEqual(opened, [30, 2]);
opened = null;
assert.strictEqual(flow.previous(state), 0);
assert.deepStrictEqual(opened, [10, 0]);

console.log("approval flow tests passed");
