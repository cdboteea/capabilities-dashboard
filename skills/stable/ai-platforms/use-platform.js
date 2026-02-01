// use-platform.js - AI Platform dispatcher implementation
// This would be called from OpenClaw skills system

function usePlatform(request) {
    const timestamp = new Date().toISOString().replace(/[-:]/g, '').slice(0, 15);
    const requestLower = request.toLowerCase();
    
    // Platform detection
    let platform = '';
    let taskType = 'standard';
    let cleanRequest = request;
    
    // Direct platform specification
    if (requestLower.match(/(chatgpt|chat gpt|gpt)/)) {
        platform = 'chatgpt';
        cleanRequest = request.replace(/^(use |ask |)?(chatgpt|chat gpt|gpt)( to| about| help with)?/i, '').trim();
    } else if (requestLower.match(/(claude app|claude desktop)/)) {
        platform = 'claude-app';
        cleanRequest = request.replace(/^(use |ask |)?(claude app|claude desktop)( to| about| help with)?/i, '').trim();
    } else if (requestLower.match(/(gemini|google gemini|bard)/)) {
        platform = 'gemini';
        cleanRequest = request.replace(/^(use |ask |)?(gemini|google gemini|bard)( to| about| help with| research)?/i, '').trim();
    } else {
        // Auto-detection based on task type
        if (requestLower.match(/(research|analyze|study|investigate|market|trends)/)) {
            platform = 'gemini';
        } else if (requestLower.match(/(code|programming|debug|algorithm|technical)/)) {
            platform = 'claude-app';
        } else if (requestLower.match(/(write|create|image|creative|story)/)) {
            platform = 'chatgpt';
        } else {
            return {
                error: 'No platform specified. Use: chatgpt/claude app/gemini + task',
                examples: [
                    'use chatgpt to write a Python script',
                    'ask claude app to analyze this architecture',
                    'gemini research market trends'
                ]
            };
        }
    }
    
    // Check for research tasks
    if (platform === 'gemini' && requestLower.match(/(research|analyze|study|investigate)/)) {
        taskType = 'research';
    }
    
    return {
        platform,
        taskType,
        cleanRequest,
        timestamp,
        originalRequest: request
    };
}

// Agent task generators
function generateChatGPTTask(cleanRequest, outputDir, originalRequest) {
    return `You are the ChatGPT App automation agent.

Task: ${cleanRequest}

Instructions:
1. Launch/focus ChatGPT app: open -a ChatGPT && sleep 3
2. Take screenshot: peekaboo image --path ${outputDir}/chatgpt-before.png --app ChatGPT
3. Start new conversation: peekaboo key 'cmd+n' && sleep 1
4. Submit request: peekaboo type '${cleanRequest}' && peekaboo key Return
5. Wait for response: sleep 90
6. Capture response: peekaboo click 'Copy' && pbpaste > ${outputDir}/response.md
7. Final screenshot: peekaboo image --path ${outputDir}/chatgpt-after.png --app ChatGPT

Save metadata to: ${outputDir}/metadata.yaml
Report back with ChatGPT's response and any issues encountered.

Original request: ${originalRequest}`;
}

function generateClaudeAppTask(cleanRequest, outputDir, originalRequest) {
    return `You are the Claude App automation agent.

Task: ${cleanRequest}

Instructions:
1. Launch/focus Claude app: open -a Claude && sleep 3
2. Take screenshot: peekaboo image --path ${outputDir}/claude-before.png --app Claude
3. Start new conversation: peekaboo key 'cmd+n' && sleep 1
4. Submit request: peekaboo type '${cleanRequest}' && peekaboo key Return
5. Wait for response: sleep 90
6. Capture response: peekaboo click 'Copy' && pbpaste > ${outputDir}/response.md
7. Final screenshot: peekaboo image --path ${outputDir}/claude-after.png --app Claude

Save metadata to: ${outputDir}/metadata.yaml
Report back with Claude's response and any issues encountered.

Original request: ${originalRequest}`;
}

function generateGeminiTask(cleanRequest, outputDir, originalRequest, taskType) {
    if (taskType === 'research') {
        return `You are the Gemini Research automation agent.

Task: ${cleanRequest}

Instructions:
1. Open Gemini: browser action=open targetUrl='https://gemini.google.com' profile=openclaw
2. Take screenshot: browser action=screenshot
3. Select Research tool: browser action=act request='{"kind": "click", "ref": "Research"}'
4. Submit research request: browser action=act request='{"kind": "type", "text": "${cleanRequest}"}'
5. Start research: browser action=act request='{"kind": "key", "key": "Enter"}'
6. Wait for research plan: browser action=act request='{"kind": "wait", "timeMs": 45000}'
7. Launch research: browser action=act request='{"kind": "click", "ref": "Launch"}'
8. Monitor progress and wait for completion (up to 20 minutes)
9. Capture final research report and save to: ${outputDir}/response.md
10. Take final screenshot: browser action=screenshot

This is a deep research task - expect 10-20 minutes for completion.
Save all screenshots to: ${outputDir}/gemini-*.png

Original request: ${originalRequest}`;
    } else {
        return `You are the Gemini Chat automation agent.

Task: ${cleanRequest}

Instructions:
1. Open Gemini: browser action=open targetUrl='https://gemini.google.com' profile=openclaw
2. Take screenshot: browser action=screenshot
3. Submit request: browser action=act request='{"kind": "type", "text": "${cleanRequest}", "ref": "textbox"}'
4. Send request: browser action=act request='{"kind": "key", "key": "Enter"}'
5. Wait for response: browser action=act request='{"kind": "wait", "timeMs": 60000}'
6. Capture response and save to: ${outputDir}/response.md
7. Take final screenshot: browser action=screenshot

Save all screenshots to: ${outputDir}/gemini-*.png

Original request: ${originalRequest}`;
    }
}

module.exports = {
    usePlatform,
    generateChatGPTTask,
    generateClaudeAppTask, 
    generateGeminiTask
};