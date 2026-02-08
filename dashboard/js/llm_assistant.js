/**
 * LLM Research Assistant - Logic Module
 * Simulates a Large Language Model interpreting natural language research events.
 */

function processLLMInput() {
    const inputField = document.getElementById('llm-input');
    const chatWindow = document.getElementById('chat-window');
    const previewArea = document.getElementById('event-structured-output');
    const text = inputField.value.trim();

    if (!text) return;

    // 1. Add User Message
    addMessage(text, 'user');
    inputField.value = "";

    // 2. Simulate "Thinking"
    const thinkingMsg = addMessage("Analyzing intent and extracting entities...", 'bot thinking');

    setTimeout(() => {
        chatWindow.removeChild(thinkingMsg);

        // 3. Simple Mock Intent Recognition
        let event = { type: 'general', severity: 'low', location: 'unknown' };

        if (text.toLowerCase().includes('aphid') || text.toLowerCase().includes('mite') || text.toLowerCase().includes('pest')) {
            event = { type: 'pest_pressure', specific: 'Entomological Issue', severity: 'high' };
        } else if (text.toLowerCase().includes('fertilizer') || text.toLowerCase().includes('nutrient')) {
            event = { type: 'fertigation', specific: 'Nutrient Flush', severity: 'medium' };
        } else if (text.toLowerCase().includes('failure') || text.toLowerCase().includes('broken') || text.toLowerCase().includes('offline')) {
            event = { type: 'equipment_failure', specific: 'Hardware Integrity', severity: 'critical' };
        }

        // 4. Update UI with "Detected" structure
        previewArea.innerHTML = `
            <div class="structured-tag">
                <strong>Intent:</strong> ${event.type} <br>
                <strong>Classification:</strong> ${event.specific || 'Standard Log'} <br>
                <strong>Pipeline Impact:</strong> Applied to ML Preprocessing
            </div>
        `;

        // 5. Physical Push to Data Backbone
        fetch('http://localhost:5000/api/event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: event.type,
                description: text,
                severity: event.severity === 'critical' ? 5 : (event.severity === 'high' ? 4 : 2),
                is_llm: true
            })
        }).then(response => {
            if (response.ok) {
                addMessage(`Event identified as a <strong>${event.type}</strong>. I've curated this entry and pushed it to the synchronization backbone for ML training.`, 'bot');
            }
        });
    }, 1500);
}

function addMessage(text, className) {
    const chatWindow = document.getElementById('chat-window');
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${className}`;
    msgDiv.innerHTML = text;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return msgDiv;
}
