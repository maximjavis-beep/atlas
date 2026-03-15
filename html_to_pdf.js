const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function convertHTMLToPDF(inputPath, outputPath) {
    if (!fs.existsSync(inputPath)) {
        console.error(`❌ 输入文件不存在: ${inputPath}`);
        process.exit(1);
    }

    console.log(`📄 正在转换: ${path.basename(inputPath)}`);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        
        // 设置视口大小，确保图片正常加载
        await page.setViewport({ width: 1280, height: 800 });
        
        // 加载 HTML 文件
        const fileUrl = 'file://' + path.resolve(inputPath);
        console.log('🌐 加载页面...');
        await page.goto(fileUrl, { waitUntil: 'networkidle2', timeout: 120000 });

        // 滚动页面触发懒加载图片
        console.log('📜 滚动页面触发图片加载...');
        await page.evaluate(async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 300;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        window.scrollTo(0, 0);
                        resolve();
                    }
                }, 100);
            });
        });

        // 等待图片加载
        console.log('⏳ 等待图片加载...');
        let lastLoadedCount = 0;
        let stableCount = 0;
        const maxWaitTime = 45000; // 最长等待 45 秒
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitTime) {
            const loadedCount = await page.evaluate(() => {
                const images = document.querySelectorAll('img');
                let count = 0;
                for (let img of images) {
                    if (img.complete && img.naturalWidth > 0) {
                        count++;
                    }
                }
                return count;
            });
            
            const totalImages = await page.evaluate(() => document.querySelectorAll('img').length);
            console.log(`  图片加载进度: ${loadedCount}/${totalImages}`);
            
            // 如果所有图片都加载完成
            if (loadedCount === totalImages && totalImages > 0) {
                console.log('✅ 所有图片加载完成');
                break;
            }
            
            // 如果加载数量稳定（没有新图片加载）
            if (loadedCount === lastLoadedCount) {
                stableCount++;
                if (stableCount >= 3) { // 连续 3 次没有变化
                    console.log(`⚠️ 图片加载稳定 (${loadedCount}/${totalImages})，继续生成 PDF`);
                    break;
                }
            } else {
                stableCount = 0;
            }
            
            lastLoadedCount = loadedCount;
            await new Promise(resolve => setTimeout(resolve, 1500));
        }

        // 额外等待确保渲染完成
        console.log('⏳ 等待渲染完成...');
        await new Promise(resolve => setTimeout(resolve, 3000));

        // 生成 PDF
        console.log('📝 生成 PDF...');
        await page.pdf({
            path: outputPath,
            format: 'A4',
            printBackground: true,
            margin: {
                top: '20mm',
                right: '15mm',
                bottom: '20mm',
                left: '15mm'
            }
        });

        console.log(`✅ PDF 已生成: ${outputPath}`);
    } catch (error) {
        console.error(`❌ 转换失败: ${error.message}`);
        process.exit(1);
    } finally {
        await browser.close();
    }
}

// 命令行参数
const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
    console.log('用法: node html_to_pdf.js <input.html> <output.pdf>');
    process.exit(1);
}

convertHTMLToPDF(inputPath, outputPath);
