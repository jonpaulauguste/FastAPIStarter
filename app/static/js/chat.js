/**
 * AI Chat Widget for Campus Eats
 */

(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChat);
    } else {
        initChat();
    }

    function initChat() {
        const chatWidget = document.getElementById('chat-widget');
        if (!chatWidget) return;

        const chatToggle = document.getElementById('chat-toggle');
        const chatContainer = document.getElementById('chat-container');
        const chatClose = document.getElementById('chat-close');
        const chatBox = document.getElementById('chat-box');
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        const suggestionChips = document.querySelectorAll('.suggestion-chip');

        let isOpen = false;
        let isLoading = false;

        // Toggle chat open/closed
        function openChat() {
            isOpen-true;
            chatContainer.classList.add('chat-open');
            chatContainer.classList.remove('chat-collapsed');
            chatToggle.style.display='none';

            if (chatBox.children.length==0){
                addMessages('ai',"👋 Hi! I'm the Campus Eats assistant. Ask me about restaurants, cuisines, or what to eat!");
                loadSuggestions();
            }
            userInput.focus();
        }

        // Close chat
        function closeChat() {
            isOpen = false;
            chatContainer.classList.remove('chat-open');
            chatContainer.classList.add('chat-collapsed');
            chatToggle.style.display = '';
        }

        // Add welcome message
        function addWelcomeMessage() {
            addMessage('ai', "👋 Hi! I'm the Campus Eats assistant. Ask me about restaurants, cuisines, or what to eat!");
        }

        // Load suggestions from API
        async function loadSuggestions() {
            try {
                const response = await fetch('/ai/chat/suggestions');
                const data = await response.json();
                updateSuggestionChips(data.suggestions);
            } catch (error) {
                console.log('Using default suggestions');
            }
        }

        // Update suggestion chips
        function updateSuggestionChips(suggestions) {
            const container = document.querySelector('.chat-suggestions');
            if (!container) return;
            
            container.innerHTML = '';
            suggestions.slice(0, 4).forEach(text => {
                const chip = document.createElement('button');
                chip.className = 'suggestion-chip';
                chip.textContent = text;
                chip.addEventListener('click', () => {
                    userInput.value = text;
                    sendMessage();
                });
                container.appendChild(chip);
            });
        }

        // Add message to chat
        function addMessage(role, text) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-message chat-${role}`;
            
            const bubble = document.createElement('div');
            bubble.className = `message-bubble message-${role}`;
            bubble.textContent = text;
            
            messageDiv.appendChild(bubble);
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        // Add loading indicator
        function addLoadingIndicator() {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'chat-message chat-ai';
            loadingDiv.id = 'loading-indicator';
            
            const bubble = document.createElement('div');
            bubble.className = 'message-bubble message-ai';
            bubble.innerHTML = '<span class="typing-dots">Thinking<span>.</span><span>.</span><span>.</span></span>';
            
            loadingDiv.appendChild(bubble);
            chatBox.appendChild(loadingDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        // Remove loading indicator
        function removeLoadingIndicator() {
            const indicator = document.getElementById('loading-indicator');
            if (indicator) indicator.remove();
        }

        // Send message to AI
        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message || isLoading) return;

            isLoading = true;
            sendBtn.disabled = true;
            userInput.disabled = true;

            addMessage('user', message);
            userInput.value = '';
            addLoadingIndicator();

            try {
                const response = await fetch('/ai/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                removeLoadingIndicator();
                addMessage('ai', data.reply);
            } catch (error) {
                removeLoadingIndicator();
                addMessage('ai', 'Sorry, I\'m having trouble connecting. Please try again later.');
                console.error('Chat error:', error);
            } finally {
                isLoading = false;
                sendBtn.disabled = false;
                userInput.disabled = false;
                userInput.focus();
            }
        }

        // Event listeners
        chatToggle.addEventListener('click', openChat);
        
        chatContainer.addEventListener('click', function(e) {
            const closeBtn= e.target.closest('#chat-close');
            if (closeBtn) closeChat();
        });

        sendBtn.addEventListener('click', sendMessage);

        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Suggestion chips
        suggestionChips.forEach(chip => {
            chip.addEventListener('click', () => {
                userInput.value = chip.textContent;
                sendMessage();
            });
        });
    }
})();
