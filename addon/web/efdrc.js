(function() {
    window.EFDRC = {
        setup: function() {
            document.addEventListener('click', function(event) {
                if (event.ctrlKey) {
                    var el = event.target;
                    while (el && el !== document.body) {
                        if (el.hasAttribute('data-efdrc-idx')) {
                            var idx = el.getAttribute('data-efdrc-idx');
                            window.pycmd('EFDRC!edit#' + idx);
                            event.preventDefault();
                            event.stopPropagation();
                            return;
                        }
                        el = el.parentElement;
                    }
                }
            }, true);

            window.addEventListener('keydown', function(e) {
                if (e.key === 'Control') document.body.classList.add('efdrc-ctrl');
            });
            window.addEventListener('keyup', function(e) {
                if (e.key === 'Control') document.body.classList.remove('efdrc-ctrl');
            });
        }
    };
    EFDRC.setup();
})();
