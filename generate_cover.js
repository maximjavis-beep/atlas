const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function generateCover() {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    // 设置视口大小为 1200x630 (Open Graph 推荐尺寸)
    await page.setViewport({ width: 1200, height: 630 });
    
    // 获取当前日期
    const today = new Date().toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    // 创建封面 HTML - 哲学主题风格
    const coverHTML = `
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                width: 1200px;
                height: 630px;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-family: 'Noto Serif SC', 'Georgia', serif;
                color: white;
                text-align: center;
                position: relative;
                overflow: hidden;
            }
            /* 装饰性圆形 */
            .circle-1 {
                position: absolute;
                width: 200px;
                height: 200px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.05);
                top: -50px;
                left: -50px;
            }
            .circle-2 {
                position: absolute;
                width: 300px;
                height: 300px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.03);
                bottom: -100px;
                right: -100px;
            }
            /* 哲学符号装饰 */
            .phil-icon {
                position: absolute;
                font-size: 50px;
                opacity: 0.2;
            }
            .icon-1 { top: 80px; left: 150px; }
            .icon-2 { top: 80px; right: 150px; }
            .icon-3 { bottom: 100px; left: 150px; }
            .icon-4 { bottom: 100px; right: 150px; }
            .main-icon {
                font-size: 100px;
                margin-bottom: 20px;
                text-shadow: 4px 4px 8px rgba(0,0,0,0.3);
            }
            .title {
                font-size: 64px;
                font-weight: bold;
                margin-bottom: 10px;
                text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
                letter-spacing: 4px;
            }
            .subtitle {
                font-size: 32px;
                opacity: 0.95;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                letter-spacing: 2px;
                margin-bottom: 15px;
            }
            .tagline {
                font-size: 22px;
                opacity: 0.9;
                letter-spacing: 3px;
                margin-bottom: 25px;
            }
            .regions {
                font-size: 18px;
                opacity: 0.85;
                letter-spacing: 4px;
            }
            .date {
                font-size: 16px;
                opacity: 0.7;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="circle-1"></div>
        <div class="circle-2"></div>
        <div class="phil-icon icon-1">⚖️</div>
        <div class="phil-icon icon-2">🏛️</div>
        <div class="phil-icon icon-3">📜</div>
        <div class="phil-icon icon-4">🦉</div>
        <div class="main-icon">🏛️</div>
        <div class="title">Atlas</div>
        <div class="subtitle">全球哲学研讨情报</div>
        <div class="tagline">思考 · 探索 · 智慧</div>
        <div class="regions">美洲 · 欧洲 · 非洲 · 亚洲</div>
        <div class="date">${today}</div>
    </body>
    </html>
    `;
    
    await page.setContent(coverHTML);
    
    // 等待字体加载
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 截图
    const outputPath = process.argv[2] || path.join(__dirname, 'web', 'cover.jpg');
    await page.screenshot({ 
        path: outputPath,
        type: 'jpeg',
        quality: 90
    });
    
    await browser.close();
    console.log(`✅ 封面已生成: ${outputPath}`);
}

generateCover().catch(err => {
    console.error('❌ 生成失败:', err);
    process.exit(1);
});
