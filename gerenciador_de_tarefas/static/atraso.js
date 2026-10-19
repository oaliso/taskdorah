(function () {
    function verificar() {
        var agora = Date.now();
        document.querySelectorAll('[data-vence]').forEach(function (el) {
            if (new Date(el.dataset.vence).getTime() < agora) {
                el.removeAttribute('data-vence');
                el.dispatchEvent(new CustomEvent('tarefa:atrasada', { bubbles: true }));
            }
        });
    }
    setInterval(verificar, 15000);
    // abas em segundo plano têm os timers atrasados pelo navegador
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) verificar();
    });
    verificar();
})();