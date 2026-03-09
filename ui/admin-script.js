// 切换标签页
function switchTab(tabName) {
    // 隐藏所有标签内容
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));
    
    // 移除所有标签的激活状态
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // 激活当前标签
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
    
    // 加载对应的数据
    if (tabName === 'knowledge-base') {
        loadKnowledgeBases();
    } else if (tabName === 'special-flows') {
        loadSpecialFlows();
    } else if (tabName === 'error-feedback') {
        loadErrorFeedbacks();
    }
}

// 显示通知
function showNotification(message, isSuccess = true) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${isSuccess ? 'success' : 'error'}`;
    notification.style.display = 'block';
    
    setTimeout(() => {
        notification.style.display = 'none';
    }, 5000);
}

// 切换知识库URL输入框显示/隐藏
function toggleKbUrlInput() {
    const urlInput = document.getElementById('kb-url');
    const editBtn = document.getElementById('kb-edit-btn');
    
    if (urlInput.classList.contains('active')) {
        // 当前是保存状态，执行保存操作
        saveKnowledgeBase();
    } else {
        // 当前是编辑状态，显示输入框并切换按钮文本
        urlInput.classList.add('active');
        editBtn.textContent = '保存';
        editBtn.className = 'btn btn-success'; // 改为绿色保存按钮
    }
}

// 格式化QA内容显示
function formatQAContent(content) {
    if (!content) return '';
    try {
        // 尝试解析JSON数组
        const qaArray = JSON.parse(content);
        if (Array.isArray(qaArray)) {
            return qaArray.map(item => 
                `${item.question || ''}\n${item.answer || ''}`
            ).join('\n\n---\n\n');
        }
    } catch (e) {
        // 如果不是JSON，直接返回原始内容
        return content;
    }
    return content;
}

// 知识库管理功能
async function loadKnowledgeBases() {
    try {
        const response = await fetch('/api/knowledge-bases');
        const data = await response.json();
        
        if (data.code === 200) {
            const tbody = document.getElementById('kb-tbody');
            tbody.innerHTML = '';
            
            data.data.forEach(kb => {
                const questionsContent = formatQAContent(kb.questions);
                const answersContent = formatQAContent(kb.answers);
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${kb.id}</td>
                    <td title="${kb.seed_url}">${kb.seed_url.length > 50 ? kb.seed_url.substring(0, 50) + '...' : kb.seed_url}</td>
                    <td title="${kb.current_url}">${kb.current_url.length > 50 ? kb.current_url.substring(0, 50) + '...' : kb.current_url}</td>
                    <td><div class="qa-content">${questionsContent.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div></td>
                    <td><div class="qa-content">${answersContent.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div></td>
                    <td>${kb.created_at}</td>
                    <td class="actions">
                        <button class="btn" onclick="viewKnowledgeBaseDetails('${kb.id}')">详情</button>
                        <button class="btn btn-danger" onclick="deleteKnowledgeBase('${kb.id}')">删除</button>
                        <button class="btn" onclick="rebuildKnowledgeBase('${kb.id}', '${kb.seed_url.replace(/'/g, "\\'")}')">重建</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        } else {
            showNotification(`加载知识库失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`加载知识库时发生错误: ${error.message}`, false);
    }
}

let editingKbId = null;

// 查看知识库详情（在新窗口或模态框中显示完整内容）
function viewKnowledgeBaseDetails(id) {
    // 这里可以实现一个详情查看功能，暂时先alert提示
    alert('点击了查看详情，ID: ' + id);
    // 实际项目中可以打开一个模态框显示完整的raw_content、questions、answers等
}

async function saveKnowledgeBase() {
    const url = document.getElementById('kb-url').value.trim();
    
    if (!url) {
        showNotification('请填写知识库URL', false);
        return;
    }
    
    try {
        document.getElementById('kb-loading').style.display = 'block';
        
        let response;
        if (editingKbId) {
            // 更新知识库
            response = await fetch(`/api/knowledge-bases/${editingKbId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url
                })
            });
        } else {
            // 创建新知识库
            response = await fetch('/api/knowledge-bases', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url
                })
            });
        }
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification(editingKbId ? '知识库更新成功' : '知识库创建成功');
            // 隐藏输入框并重置
            resetKbForm();
            loadKnowledgeBases(); // 重新加载列表
        } else {
            showNotification(`操作失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`保存知识库时发生错误: ${error.message}`, false);
    } finally {
        document.getElementById('kb-loading').style.display = 'none';
    }
}

// 重置知识库表单
function resetKbForm() {
    const urlInput = document.getElementById('kb-url');
    const editBtn = document.getElementById('kb-edit-btn');
    
    urlInput.classList.remove('active');
    urlInput.value = '';
    editBtn.textContent = '编辑';
    editBtn.className = 'btn'; // 恢复为蓝色编辑按钮
    editingKbId = null;
}

async function deleteKnowledgeBase(id) {
    if (!confirm('确定要删除这个知识库吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/knowledge-bases/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('知识库删除成功');
            loadKnowledgeBases(); // 重新加载列表
        } else {
            showNotification(`删除失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`删除知识库时发生错误: ${error.message}`, false);
    }
}

async function rebuildKnowledgeBase(id, url) {
    if (!confirm('确定要重建这个知识库吗？这将重新爬取该URL的内容。')) {
        return;
    }
    
    try {
        document.getElementById('kb-loading').style.display = 'block';
        
        const response = await fetch('/api/crawler/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                seed_url: url
            })
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('知识库重建任务已启动');
        } else {
            showNotification(`重建任务启动失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`启动重建任务时发生错误: ${error.message}`, false);
    } finally {
        document.getElementById('kb-loading').style.display = 'none';
    }
}

// 特殊问题流程管理功能
async function loadSpecialFlows() {
    try {
        const response = await fetch('/api/special-flows');
        const data = await response.json();
        
        if (data.code === 200) {
            const tbody = document.getElementById('flows-tbody');
            tbody.innerHTML = '';
            
            data.data.forEach(flow => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${flow.key}</td>
                    <td>${flow.desc}</td>
                    <td>${flow.prompt}</td>
                    <td>${flow.status}</td>
                    <td class="actions">
                        <button class="btn" onclick="editSpecialFlow('${flow.key.replace(/'/g, "\\'")}', '${flow.desc.replace(/'/g, "\\'")}', '${flow.prompt.replace(/'/g, "\\'")}', '${flow.status}')">编辑</button>
                        <button class="btn btn-danger" onclick="deleteSpecialFlow('${flow.key.replace(/'/g, "\\'")}')">删除</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        } else {
            showNotification(`加载特殊流程失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`加载特殊流程时发生错误: ${error.message}`, false);
    }
}

let editingFlowKey = null;

function editSpecialFlow(key, desc, prompt, status) {
    document.getElementById('flow-key').value = key;
    document.getElementById('flow-desc').value = desc;
    document.getElementById('flow-prompt').value = prompt;
    document.getElementById('flow-status').value = status;
    editingFlowKey = key;
}

async function saveSpecialFlow() {
    const key = document.getElementById('flow-key').value.trim();
    const desc = document.getElementById('flow-desc').value.trim();
    const prompt = document.getElementById('flow-prompt').value.trim();
    const status = document.getElementById('flow-status').value;
    
    if (!key) {
        showNotification('请填写流程标识', false);
        return;
    }
    
    if (!desc) {
        showNotification('请填写流程描述', false);
        return;
    }
    
    if (!prompt) {
        showNotification('请填写处理提示', false);
        return;
    }
    
    try {
        document.getElementById('flow-loading').style.display = 'block';
        
        let response;
        if (editingFlowKey) {
            // 更新流程
            response = await fetch(`/api/special-flows/${editingFlowKey}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    desc: desc,
                    prompt: prompt,
                    status: status
                })
            });
        } else {
            // 创建新流程
            response = await fetch('/api/special-flows', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    key: key,
                    desc: desc,
                    prompt: prompt,
                    status: status
                })
            });
        }
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification(editingFlowKey ? '特殊流程更新成功' : '特殊流程创建成功');
            document.getElementById('flow-key').value = '';
            document.getElementById('flow-desc').value = '';
            document.getElementById('flow-prompt').value = '';
            document.getElementById('flow-status').value = 'active';
            editingFlowKey = null;
            loadSpecialFlows(); // 重新加载列表
        } else {
            showNotification(`操作失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`保存特殊流程时发生错误: ${error.message}`, false);
    } finally {
        document.getElementById('flow-loading').style.display = 'none';
    }
}

async function deleteSpecialFlow(key) {
    if (!confirm('确定要删除这个特殊流程吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/special-flows/${key}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('特殊流程删除成功');
            loadSpecialFlows(); // 重新加载列表
        } else {
            showNotification(`删除失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`删除特殊流程时发生错误: ${error.message}`, false);
    }
}

// 错误反馈管理功能
let currentFeedbackId = null;

async function loadErrorFeedbacks() {
    try {
        document.getElementById('feedback-loading').style.display = 'block';
        
        const response = await fetch('/api/error-feedback');
        const data = await response.json();
        
        if (data.code === 200) {
            const tbody = document.getElementById('feedback-tbody');
            tbody.innerHTML = '';
            
            data.data.forEach(fb => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${fb.feedback_id}</td>
                    <td>${fb.session_id}</td>
                    <td>${fb.question}</td>
                    <td>${fb.robot_reply}</td>
                    <td>${fb.error_type}</td>
                    <td>${fb.error_desc}</td>
                    <td>${fb.create_time}</td>
                    <td>${fb.fix_status}</td>
                    <td>${fb.fix_time || '-'}</td>
                    <td class="actions">
                        <button class="btn" onclick="showUpdateFeedbackModal('${fb.feedback_id}', '${fb.fix_status.replace(/'/g, "\\'")}', '${fb.error_desc.replace(/'/g, "\\'")}')">修改状态</button>
                        <button class="btn btn-danger" onclick="deleteErrorFeedback('${fb.feedback_id}')">删除</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        } else {
            showNotification(`加载错误反馈失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`加载错误反馈时发生错误: ${error.message}`, false);
    } finally {
        document.getElementById('feedback-loading').style.display = 'none';
    }
}

// 显示修改反馈状态的模态框
function showUpdateFeedbackModal(feedbackId, currentStatus, currentDesc) {
    currentFeedbackId = feedbackId;
    document.getElementById('update-fix-status').value = currentStatus;
    document.getElementById('update-error-desc').value = currentDesc || '';
    
    const modal = document.getElementById('feedbackModal');
    modal.style.display = 'block';
    
    // 添加关闭事件监听器
    const span = document.getElementsByClassName('close')[0];
    span.onclick = function() {
        modal.style.display = 'none';
    };
    
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

// 更新反馈状态
async function updateFeedbackStatus() {
    const fixStatus = document.getElementById('update-fix-status').value;
    const errorDesc = document.getElementById('update-error-desc').value.trim();
    
    if (!currentFeedbackId) {
        showNotification('无效的反馈ID', false);
        return;
    }
    
    try {
        const payload = { fix_status: fixStatus };
        if (errorDesc) {
            payload.error_desc = errorDesc;
        }
        
        const response = await fetch(`/api/error-feedback/${currentFeedbackId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('反馈状态更新成功');
            document.getElementById('feedbackModal').style.display = 'none';
            loadErrorFeedbacks(); // 重新加载列表
        } else {
            showNotification(`更新失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`更新反馈状态时发生错误: ${error.message}`, false);
    }
}

async function deleteErrorFeedback(feedbackId) {
    if (!confirm('确定要删除这条错误反馈吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/error-feedback/${feedbackId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('错误反馈删除成功');
            loadErrorFeedbacks(); // 重新加载列表
        } else {
            showNotification(`删除失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`删除错误反馈时发生错误: ${error.message}`, false);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 默认加载知识库数据
    loadKnowledgeBases();
});