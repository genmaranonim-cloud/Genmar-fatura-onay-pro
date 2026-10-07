(function (global) {
    "use strict";

    function move(offset, state) {
        if (state.blocked) return state.index;
        const items = state.items || [];
        const nextIndex = state.index + offset;
        if (nextIndex < 0 || nextIndex >= items.length) return state.index;
        state.open(items[nextIndex]);
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
        async afterApproval(state) {
            // Refresh the approved invoice itself. Never select the next one.
            await state.open(state.id);
            return state.id;
        },
    };

    global.GenmarApprovalFlow = Object.freeze(approvalFlow);
})(window);
