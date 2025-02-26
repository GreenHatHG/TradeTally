<script>
document.addEventListener('DOMContentLoaded', function() {
  // 等待Plotly图表完全渲染后再执行我们的代码
  setTimeout(function() {
    console.log('旭日图增强脚本启动...');
    let gd = document.getElementById('sunburst-chart');
    
    // 检查元素是否存在
    if (!gd) {
      console.log('未找到ID为sunburst-chart的元素，尝试查找其他Plotly容器');
      // 尝试查找任何Plotly图表容器
      const plotlyElements = document.querySelectorAll('.plotly-graph-div');
      if (plotlyElements.length > 0) {
        gd = plotlyElements[0];
        console.log('找到替代图表容器:', gd.id);
      } else {
        console.error('找不到任何Plotly图表容器');
        return; // 如果找不到任何图表容器，则退出
      }
    } else {
      console.log('找到指定ID的图表容器: sunburst-chart');
    }
    
    // 修复文本分行问题
    const fixTextLineBreaks = function() {
      // 找到所有旭日图文本元素
      const textElements = gd.querySelectorAll('g.sunburstlayer g.slicetext text');
      
      if (!textElements || textElements.length === 0) {
        console.warn('未找到旭日图文本元素，可能是选择器不匹配');
        return;
      }
      
      console.log(`找到 ${textElements.length} 个文本元素`);
      
      textElements.forEach(text => {
        // 获取当前data-unformatted属性值并移除<br>
        const unformatted = text.getAttribute('data-unformatted');
        if (unformatted && unformatted.includes('<br>')) {
          // 替换换行为空格
          const newText = unformatted.replace(/<br>/g, ' ');
          text.setAttribute('data-unformatted', newText);
          
          // 删除所有tspan元素
          while (text.firstChild) {
            text.removeChild(text.firstChild);
          }
          
          // 创建单个tspan元素
          const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
          tspan.setAttribute('class', 'line');
          tspan.setAttribute('dy', '0em');
          tspan.setAttribute('x', '0');
          tspan.setAttribute('y', '0');
          tspan.textContent = newText;
          text.appendChild(tspan);
        }
      });
    };
    
    // 执行修复
    fixTextLineBreaks();
    
    // Python传递的百分比数据 - 将在Python中动态替换这个变量
    const pythonPercentages = JSON_DATA_FROM_PYTHON || {};
    
    // 应用百分比修复
    const fixPercentages = function() {
      // 获取所有需修复的文本元素
      const textElements = gd.querySelectorAll('text');
      let fixCount = 0;
      
      textElements.forEach((elem, i) => {
        const currentText = elem.textContent;
        if (currentText && (currentText.includes('NaN%') || currentText.match(/\d+\.\d+%$/))) {
          // 找出对应的扇形路径
          const parent = elem.closest('g.slice') || elem.parentNode.parentNode;
          if (!parent) return;
          
          const path = parent.querySelector('path');
          if (!path || !path.__data__) return;
          
          const pathData = path.__data__;
          
          // 提取标签和ID
          let label = '';
          let id = '';
          
          if (pathData.data) {
            label = pathData.data.label || '';
            id = pathData.data.id || '';
          }
          
          console.log(`处理文本: "${currentText}", ID: ${id}, 标签: ${label}`);
          
          // 获取正确的百分比值
          let percentage = null;
          
          // 从Python传递的数据中查找百分比
          if (id && pythonPercentages[id] !== undefined) {
            percentage = pythonPercentages[id];
            console.log(`使用Python百分比数据: ${percentage.toFixed(1)}%`);
          } else {
            console.log(`未找到ID "${id}" 的Python数据，尝试提取标签`);
            
            // 从文本中提取标签部分
            const textLabel = currentText.split(/\s+\d+\.?\d*%/).shift().trim();
            console.log(`从文本提取标签: "${textLabel}"`);
            
            // 尝试通过标签匹配
            for (const k in pythonPercentages) {
              if (k.endsWith('/' + textLabel) || k.endsWith('/' + label)) {
                percentage = pythonPercentages[k];
                console.log(`通过标签 "${textLabel}" 找到匹配的百分比: ${percentage.toFixed(1)}%`);
                break;
              }
            }
          }
          
          // 应用找到的百分比
          if (percentage !== null) {
            const formattedPerc = percentage.toFixed(1);
            // 保留原始标签部分
            const labelPart = currentText.split(/\s+\d+\.?\d*%|NaN%/).shift().trim();
            const newText = `${labelPart} ${formattedPerc}%`;
            
            // 更新文本
            elem.textContent = newText;
            
            // 更新data-unformatted属性
            if (elem.hasAttribute('data-unformatted')) {
              elem.setAttribute('data-unformatted', newText);
            }
            
            // 更新tspan
            const tspans = elem.querySelectorAll('tspan');
            tspans.forEach(tspan => {
              tspan.textContent = newText;
            });
            
            console.log(`文本已更新: "${currentText}" -> "${newText}"`);
            fixCount++;
          } else {
            console.warn(`未找到 "${label}" 的百分比值`);
          }
        }
      });
      
      console.log(`修复了 ${fixCount} 个百分比显示问题`);
    };
    
    // 执行百分比修复
    setTimeout(() => fixPercentages(), 500);
    
    console.log('旭日图增强脚本完成');
  }, 1500); // 延迟1.5秒等待Plotly完全渲染
});
</script> 