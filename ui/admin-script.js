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
    const urlDisplay = document.getElementById('kb-url-display');
    const editBtn = document.getElementById('kb-edit-btn');
    const rebuildBtn = document.getElementById('kb-rebuild-btn');
    
    if (urlInput.style.display === 'block') {
        // 当前是保存状态，执行保存操作
        saveKnowledgeBase();
    } else {
        // 当前是显示状态，切换到编辑状态
        urlInput.style.display = 'block';
        urlDisplay.style.display = 'none';
        urlInput.value = urlDisplay.textContent === '未设置' ? '' : urlDisplay.textContent;
        editBtn.textContent = '保存';
        editBtn.className = 'btn btn-success'; // 改为绿色保存按钮
        // 如果有配置的URL，显示重建按钮
        if (urlDisplay.textContent !== '未设置' && urlDisplay.textContent !== '加载失败') {
            rebuildBtn.style.display = 'inline-block';
        }
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
                        <button class="btn" onclick="editKnowledgeBaseUrl('${kb.id}', '${kb.seed_url.replace(/'/g, "\\'")}')">编辑URL</button>
                        <button class="btn" onclick="rebuildKnowledgeBase('${kb.id}')">重新生成</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
            
            // 同时加载当前配置的URL到输入框（如果存在）
            loadCurrentKnowledgeBaseUrl();
        } else {
            showNotification(`加载知识库失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`加载知识库时发生错误: ${error.message}`, false);
    }
}

// 加载当前配置的知识库URL
async function loadCurrentKnowledgeBaseUrl() {
    try {
        const response = await fetch('/api/config/knowledge-base-url');
        const data = await response.json();
        
        if (data.code === 200) {
            const urlDisplay = document.getElementById('kb-url-display');
            const rebuildBtn = document.getElementById('kb-rebuild-btn');
            if (data.data.url) {
                urlDisplay.textContent = data.data.url;
                urlDisplay.classList.remove('empty');
                // 有URL配置时显示重建按钮
                rebuildBtn.style.display = 'inline-block';
            } else {
                urlDisplay.textContent = '未设置';
                urlDisplay.classList.add('empty');
                rebuildBtn.style.display = 'none';
            }
            // 同时也设置input的值，以便编辑时使用
            const urlInput = document.getElementById('kb-url');
            urlInput.value = data.data.url || '';
        }
    } catch (error) {
        console.log('加载当前知识库URL配置失败:', error);
        const urlDisplay = document.getElementById('kb-url-display');
        const rebuildBtn = document.getElementById('kb-rebuild-btn');
        urlDisplay.textContent = '加载失败';
        urlDisplay.classList.add('empty');
        rebuildBtn.style.display = 'none';
    }
}

// 知识库管理相关变量
let editingKbId = null;
let editingKbOriginalUrl = null;

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
        
        // 调用配置API只更新配置
        const response = await fetch('/api/config/knowledge-base-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url
            })
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('知识库URL配置已保存');
            // 隐藏输入框并重置
            resetKbForm();
            loadKnowledgeBases(); // 重新加载列表以显示最新配置状态
        } else {
            showNotification(`保存配置失败: ${data.msg}`, false);
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
    const urlDisplay = document.getElementById('kb-url-display');
    const editBtn = document.getElementById('kb-edit-btn');
    const rebuildBtn = document.getElementById('kb-rebuild-btn');
    
    urlInput.style.display = 'none';
    urlDisplay.style.display = 'block';
    editBtn.textContent = '编辑';
    editBtn.className = 'btn';
    // 根据是否有配置URL决定是否显示重建按钮
    if (urlDisplay.textContent !== '未设置' && urlDisplay.textContent !== '加载失败') {
        rebuildBtn.style.display = 'inline-block';
    } else {
        rebuildBtn.style.display = 'none';
    }
    editingKbId = null;
    editingKbOriginalUrl = null; // 重置原始URL
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

// 编辑知识库URL
function editKnowledgeBaseUrl(id, currentUrl) {
    const urlInput = document.getElementById('kb-url');
    const editBtn = document.getElementById('kb-edit-btn');
    const rebuildBtn = document.getElementById('kb-rebuild-btn');
    
    // 设置当前URL到输入框
    urlInput.value = currentUrl;
    urlInput.classList.add('active');
    editBtn.textContent = '保存';
    editBtn.className = 'btn btn-success';
    editingKbId = id;
    editingKbOriginalUrl = currentUrl; // 保存原始URL
    rebuildBtn.style.display = 'inline-block';
}

// 重新生成知识库（重新爬取）
async function rebuildKnowledgeBase(id) {
    if (!confirm('确定要重新生成这个知识库吗？这将根据当前知识库URL重新爬取数据。')) {
        return;
    }
    
    try {
        document.getElementById('kb-loading').style.display = 'block';
        
        // 调用正确的API接口：/api/knowledge-bases/rebuild/{id}
        const response = await fetch(`/api/knowledge-bases/rebuild/${id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('知识库重新生成任务已完成');
            loadKnowledgeBases(); // 重新加载列表以显示最新数据
        } else {
            showNotification(`重新生成失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`重新生成知识库时发生错误: ${error.message}`, false);
    } finally {
        document.getElementById('kb-loading').style.display = 'none';
    }
}

// 重建当前配置的知识库
async function rebuildCurrentKnowledgeBase() {
    if (!confirm('确定要重建当前配置的知识库吗？这将清空现有数据并重新爬取。')) {
        return;
    }
    
    try {
        document.getElementById('kb-loading').style.display = 'block';
        
        const response = await fetch('/api/knowledge-bases/rebuild-current', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification('知识库重建任务已完成');
            loadKnowledgeBases(); // 重新加载列表以显示最新数据
        } else {
            showNotification(`重建失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`重建知识库时发生错误: ${error.message}`, false);
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
                const statusText = flow.status === 'active' ? '启用' : '禁用';
                const statusClass = flow.status === 'active' ? '' : 'btn-secondary';
                const toggleText = flow.status === 'active' ? '禁用' : '启用';
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${flow.key}</td>
                    <td>${flow.desc}</td>
                    <td>${flow.prompt}</td>
                    <td>${statusText}</td>
                    <td class="actions">
                        <button class="btn" onclick="editSpecialFlow('${flow.key.replace(/'/g, "\\'")}', '${flow.desc.replace(/'/g, "\\'")}', '${flow.prompt.replace(/'/g, "\\'")}', '${flow.status}')">编辑</button>
                        <button class="btn ${statusClass}" onclick="toggleSpecialFlowStatus('${flow.key.replace(/'/g, "\\'")}', '${flow.status}')">${toggleText}</button>
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

// 显示特殊流程模态框
function showFlowModal() {
    document.getElementById('flowModalTitle').textContent = '新增特殊流程';
    document.getElementById('flow-key').value = '';
    document.getElementById('flow-desc').value = '';
    document.getElementById('flow-prompt').value = '';
    document.getElementById('flow-status').value = 'active';
    editingFlowKey = null;
    document.getElementById('flowModal').style.display = 'block';
    
    // 添加关闭事件监听器
    setupFlowModalClose();
}

// 关闭特殊流程模态框
function closeFlowModal() {
    document.getElementById('flowModal').style.display = 'none';
}

// 设置模态框关闭事件
function setupFlowModalClose() {
    const modal = document.getElementById('flowModal');
    const span = modal.querySelector('.close');
    
    // 确保只添加一次事件监听器
    if (!modal.dataset.hasClickListener) {
        span.onclick = function() {
            closeFlowModal();
        };
        
        window.onclick = function(event) {
            if (event.target === modal) {
                closeFlowModal();
            }
        };
        
        modal.dataset.hasClickListener = 'true';
    }
}

let editingFlowKey = null;

function editSpecialFlow(key, desc, prompt, status) {
    document.getElementById('flowModalTitle').textContent = '编辑特殊流程';
    document.getElementById('flow-key').value = key;
    document.getElementById('flow-desc').value = desc;
    document.getElementById('flow-prompt').value = prompt;
    document.getElementById('flow-status').value = status;
    editingFlowKey = key;
    document.getElementById('flowModal').style.display = 'block';
    setupFlowModalClose();
}

// 切换特殊流程状态（启用/禁用）
async function toggleSpecialFlowStatus(key, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
    const confirmText = newStatus === 'active' ? '确定要启用这个特殊流程吗？' : '确定要禁用这个特殊流程吗？';
    
    if (!confirm(confirmText)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/special-flows/${key}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: newStatus
            })
        });
        
        const data = await response.json();
        
        if (data.code === 200) {
            showNotification(newStatus === 'active' ? '特殊流程已启用' : '特殊流程已禁用');
            loadSpecialFlows(); // 重新加载列表
        } else {
            showNotification(`操作失败: ${data.msg}`, false);
        }
    } catch (error) {
        showNotification(`切换状态时发生错误: ${error.message}`, false);
    }
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
            closeFlowModal();
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
    // 默认加载第一个标签页的内容
    loadKnowledgeBases();
    
    // 确保在页面加载时也加载当前的知识库URL配置（但不显示输入框）
    loadCurrentKnowledgeBaseUrl();
});