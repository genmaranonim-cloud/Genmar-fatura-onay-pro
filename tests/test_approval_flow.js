const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync("static/approval_flow.js", "utf8"), context);
const flow = context.window.GenmarApprovalFlow;

assert.strictEqual(flow.autoAdvanceAfterApproval, false);

let opened = null;
const state = { items: [10, 20, 30], index: 1, blocked: false, open: id => { opened = id; } };
assert.strictEqual(flow.next(state), 2);
assert.strictEqual(opened, 30);
opened = null;
assert.strictEqual(flow.previous({...state, blocked: true}), 1);
assert.strictEqual(opened, null);

(async () => {
    await flow.afterApproval({id: 20, open: async id => { opened = id; }});
    assert.strictEqual(opened, 20);
    console.log("approval flow tests passed");
})().catch(error => { console.error(error); process.exit(1); });
