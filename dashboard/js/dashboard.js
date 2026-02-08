/**
 * G.O.S. Galaxy Dashboard Logic - Thread Mesh & Physics Validation
 */

document.addEventListener('DOMContentLoaded', () => {
    initTopology();
    startPhytotronSimulation();
});

function initTopology() {
    const map = document.getElementById('topology_map');
    const width = map.clientWidth;
    const height = map.clientHeight;

    // OTBR (Leader)
    const leader = createNodeBubble(width / 2, height / 2, 'OTBR', true);
    map.appendChild(leader);

    // Routers and Children (40 nodes)
    for (let i = 1; i <= 40; i++) {
        // Spiral distribution
        const angle = i * 0.5;
        const radius = 40 + i * 4;
        const x = width / 2 + Math.cos(angle) * radius;
        const y = height / 2 + Math.sin(angle) * radius;

        const isRouter = i % 8 === 0;
        const bubble = createNodeBubble(x, y, i, isRouter);
        map.appendChild(bubble);
    }
}

function createNodeBubble(x, y, label, isRouter) {
    const div = document.createElement('div');
    div.className = `node-bubble ${isRouter ? 'router' : ''}`;
    div.style.left = `${x}px`;
    div.style.top = `${y}px`;
    div.innerText = label;
    return div;
}

function startPhytotronSimulation() {
    setInterval(() => {
        // Simulate jitter in the mesh health
        const health = (98 + Math.random() * 2).toFixed(1);
        document.getElementById('mesh-health').innerText = `Nominal (${health}%)`;
    }, 4000);
}

function startCommissioning() {
    const panel = document.getElementById('comm_panel');
    const newEui = `EUI64-${Math.floor(Math.random() * 999).toString().padStart(3, '0')}`;
    document.getElementById('eui64').innerText = newEui;
}
