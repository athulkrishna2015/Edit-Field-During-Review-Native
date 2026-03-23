(function() {
    window.EFDRC = {
        config: {
            modifier: 'Ctrl',
            action: 'Click'
        },
        setup: function(conf) {
            if (conf) this.config = conf;
            
            const handleTrigger = (event) => {
                const modifierMap = {
                    'Ctrl': event.ctrlKey || event.metaKey,
                    'Shift': event.shiftKey,
                    'Alt': event.altKey,
                    'None': true
                };
                
                if (modifierMap[this.config.modifier]) {
                    let el = event.target;
                    while (el && el !== document.body) {
                        if (el.hasAttribute('data-efdrc-idx')) {
                            const idx = el.getAttribute('data-efdrc-idx');
                            window.pycmd('EFDRC!edit#' + idx);
                            event.preventDefault();
                            event.stopPropagation();
                            return;
                        }
                        el = el.parentElement;
                    }
                }
            };

            const eventType = this.config.action === 'DoubleClick' ? 'dblclick' : 'click';
            document.addEventListener(eventType, handleTrigger, true);

            const updateActiveState = (e, isDown) => {
                const keys = {
                    'Ctrl': ['Control', 'Meta'],
                    'Shift': ['Shift'],
                    'Alt': ['Alt']
                };
                if (this.config.modifier === 'None') {
                    document.body.classList.add('efdrc-active');
                } else if ((keys[this.config.modifier] || []).includes(e.key)) {
                    if (isDown) document.body.classList.add('efdrc-active');
                    else document.body.classList.remove('efdrc-active');
                }
            };

            window.addEventListener('keydown', (e) => updateActiveState(e, true));
            window.addEventListener('keyup', (e) => updateActiveState(e, false));
            window.addEventListener('blur', () => document.body.classList.remove('efdrc-active'));
            
            if (this.config.modifier === 'None') document.body.classList.add('efdrc-active');
        }
    };
})();
