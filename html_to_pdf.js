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
        
        // 加载 HTML 文件
        const fileUrl = 'file://' + path.resolve(inputPath);
        await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 60000 });

        // 等待内容加载
        await new Promise(resolve => setTimeout(resolve, 2000));

        // 生成 PDF
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
