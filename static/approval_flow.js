(function (global) {
    "use strict";

    function move(offset, state) {
        const items = state.items || [];
        const nextIndex = state.index + offset;
        if (nextIndex < 0 || nextIndex >= items.length) return state.index;
        state.open(items[nextIndex], nextIndex);
        return nextIndex;
    }

    const approvalFlow = {
        autoAdvanceAfterApproval: false,
        previous(state) {
            return move(-1, state);
        },
        next(state) {
            return move(1, state);
        },
        afterApproval() {
            // Deliberately stay on the approved invoice. Navigation is manual.
            return false;
        },
    };

    global.GenmarApprovalFlow = Object.freeze(approvalFlow);
})(window);
