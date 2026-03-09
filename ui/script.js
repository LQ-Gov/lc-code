// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const suggestionBtns = document.querySelectorAll('.suggestion-btn');

// 错误反馈相关元素
const errorFeedbackModal = document.getElementById('errorFeedbackModal');
const closeModal = document.querySelector('.close');
const submitFeedbackBtn = document.getElementById('submitFeedbackBtn');
const errorTypeSelect = document.getElementById('errorType');
const errorDescriptionTextarea = document.getElementById('errorDescription');
const errorFeedbackBtn = document.getElementById('errorFeedbackBtn'); // 错误反馈按钮

// 转人工相关元素
const transferToHumanModal = document.getElementById('transferToHumanModal');
const transferClose = document.querySelector('.transfer-close');
const cancelTransferBtn = document.getElementById('cancelTransferBtn');
const confirmTransferBtn = document.getElementById('confirmTransferBtn');
const transferToHumanBtn = document.getElementById('transferToHumanBtn'); // 转人工按钮

// Session management
let sessionId = null;
let currentQuestion = ''; // 存储当前问题
let currentReply = ''; // 存储当前回复
const userId = 'user_' + Date.now(); // Simple user ID generation

// Initialize chat with welcome message
window.addEventListener('DOMContentLoaded', () => {
    addBotMessage('您好！我是客服AI机器人，请问有什么可以帮您的吗？😊');
});

// Event Listeners
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Add suggestion button event listeners
suggestionBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const text = btn.getAttribute('data-text');
        userInput.value = text;
        sendMessage();
    });
});

// 错误反馈按钮事件监听
errorFeedbackBtn.addEventListener('click', showFeedbackModal);

// 转人工按钮事件监听
transferToHumanBtn.addEventListener('click', showTransferToHumanModal);

// Auto-resize textarea
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 100) + 'px';
});

// 错误反馈模态框事件
closeModal.addEventListener('click', () => {
    errorFeedbackModal.style.display = 'none';
});

// 转人工模态框事件
transferClose.addEventListener('click', () => {
    transferToHumanModal.style.display = 'none';
});

cancelTransferBtn.addEventListener('click', () => {
    transferToHumanModal.style.display = 'none';
});

confirmTransferBtn.addEventListener('click', transferToHuman);

window.addEventListener('click', (event) => {
    if (event.target === errorFeedbackModal) {
        errorFeedbackModal.style.display = 'none';
    }
    
    if (event.target === transferToHumanModal) {
        transferToHumanModal.style.display = 'none';
    }
});

// 提交错误反馈
submitFeedbackBtn.addEventListener('click', submitErrorFeedback);

// Send message function
async function sendMessage() {
    const message = userInput.value.trim();
    if (message) {
        addUserMessage(message);
        currentQuestion = message; // 保存当前问题
        userInput.value = '';
        userInput.style.height = 'auto';
        
        try {
            // Show loading indicator
            const loadingMessage = addLoadingMessage();
            
            // Call the backend API
            const response = await callBackendAPI(message);
            
            // Remove loading indicator
            chatMessages.removeChild(loadingMessage);
            
            // Display bot response
            addBotMessage(response.data.reply);
            
            // 保存当前回复
            currentReply = response.data.reply;
            
            // 更新会话ID供下次请求使用
            sessionId = response.data.session_id;
            
        } catch (error) {
            // Remove loading indicator
            const loadingElements = chatMessages.querySelectorAll('.loading-message');
            if (loadingElements.length > 0) {
                chatMessages.removeChild(loadingElements[loadingElements.length - 1]);
            }
            
            // Handle error
            console.error('API Error:', error);
            addBotMessage('抱歉，服务暂时不可用。请稍后再试或联系技术支持。');
        }
    }
}

// Add user message to chat
function addUserMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message user-message`;
    
    const messageText = document.createElement('div');
    messageText.textContent = message;
    
    const timeElement = document.createElement('div');
    timeElement.className = 'message-time';
    timeElement.textContent = getCurrentTime();
    
    messageDiv.appendChild(messageText);
    messageDiv.appendChild(timeElement);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Add bot message to chat (简化版本，移除操作按钮)
function addBotMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message bot-message`;
    
    const messageText = document.createElement('div');
    messageText.textContent = message;
    
    const timeElement = document.createElement('div');
    timeElement.className = 'message-time';
    timeElement.textContent = getCurrentTime();
    
    messageDiv.appendChild(messageText);
    messageDiv.appendChild(timeElement);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// 显示错误反馈模态框
function showFeedbackModal() {
    // 清空表单
    errorTypeSelect.value = '知识库未匹配到正确答案';
    errorDescriptionTextarea.value = '';
    errorFeedbackModal.style.display = 'block';
}

// 显示转人工确认模态框
function showTransferToHumanModal() {
    transferToHumanModal.style.display = 'block';
}

// 转人工处理函数
async function transferToHuman() {
    try {
        // 这里可以调用后端API来请求转接人工客服
        // 目前先模拟成功转接
        
        // 关闭确认模态框
        transferToHumanModal.style.display = 'none';
        
        // 添加系统消息告知用户已转接
        addBotMessage('正在为您转接人工客服，请稍候...');
        
        // 模拟转接成功后的消息
        setTimeout(() => {
            addBotMessage('已成功转接至人工客服。人工客服将在工作时间内（9:00-18:00）为您提供服务。');
        }, 2000);
        
        // 这里可以禁用输入框或添加其他转接后的UI状态
        // userInput.disabled = true;
        // sendButton.disabled = true;
        
    } catch (error) {
        console.error('转接人工客服失败:', error);
        alert('转接失败，请稍后再试或联系技术支持。');
    }
}

// 提交错误反馈
async function submitErrorFeedback() {
    const errorType = errorTypeSelect.value;
    const errorDesc = errorDescriptionTextarea.value.trim();
    
    if (!errorDesc) {
        alert('请填写详细的错误描述');
        return;
    }
    
    try {
        // 准备请求数据
        const feedbackData = {
            session_id: sessionId,
            question: currentQuestion,
            robot_reply: currentReply,
            error_type: errorType,
            error_desc: errorDesc
        };
        
        // 发送反馈到后端
        const response = await fetch('/api/error-feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(feedbackData)
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            alert('错误反馈提交成功，感谢您的反馈！');
            errorFeedbackModal.style.display = 'none';
        } else {
            alert(`提交失败: ${result.msg}`);
        }
    } catch (error) {
        console.error('提交错误反馈时出错:', error);
        alert('提交失败，请稍后再试');
    }
}

// Get current time in HH:MM format
function getCurrentTime() {
    const now = new Date();
    return now.getHours().toString().padStart(2, '0') + ':' + 
           now.getMinutes().toString().padStart(2, '0');
}

// Scroll to bottom of chat
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Call backend API
async function callBackendAPI(question) {
    const apiUrl = '/api/robot/consult'; // Relative URL for local development
    
    const requestBody = {
        user_id: userId,
        question: question,
        session_id: sessionId || undefined
    };
    
    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.code !== 200) {
        throw new Error(data.msg || 'API request failed');
    }
    
    return data;
}

// Add loading message
function addLoadingMessage() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot-message loading-message';
    loadingDiv.innerHTML = `
        <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <div class="message-time">${getCurrentTime()}</div>
    `;
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();
    return loadingDiv;
}

// Handle window resize for better mobile experience
window.addEventListener('resize', () => {
    scrollToBottom();
});