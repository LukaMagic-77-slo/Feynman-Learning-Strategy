import {test,expect} from '@playwright/test';
const usage={seconds:1.2,total_tokens:230,estimated_cost:.0008,model:'test'};
test('问答、反馈、主题练习和响应式布局',async({page})=>{
  const failures=[];page.on('pageerror',e=>failures.push(e.message));
  let qaCalls=0,judgeCalls=0;const votes=[];
  await page.route('**/api/qa',route=>{qaCalls++;return route.fulfill({json:{
    question:JSON.parse(route.request().postData()).question,
    answer:'概率密度可以大于 1。**概率是区间上的积分**，例如：\\(f(x)=4\\)。',
    record_id:101,usage,sources:[{id:'prob-cont-pdf-005',topic:'概率密度函数：密度可以大于1'}]}});});
  await page.route('**/api/feedback',route=>{votes.push(JSON.parse(route.request().postData()));return route.fulfill({json:{id:1}});});
  await page.route('**/api/sections',route=>route.fulfill({json:['连续型随机变量与常见分布']}));
  await page.route('**/api/topics?*',route=>route.fulfill({json:['正态分布：标准化','指数分布：无记忆性']}));
  await page.route('**/api/practice/questions',route=>route.fulfill({json:{
    exercise_id:'test-exercise',question:'为什么标准化时要除以标准差？',record_id:201,usage}}));
  await page.route('**/api/practice/test-exercise/judge',route=>{judgeCalls++;return route.fulfill({json:{
    exercise_id:'test-exercise',user_answer:'消除尺度影响',record_id:202,usage,
    evaluation:{score:'partial',reasoning:'已理解尺度转换，还可以补充均值归零。',missing_points:['解释减去均值的作用'],errors:[],suggestion:'试着比较方差和标准差的单位。'}}});});
  await page.goto('/');
  await expect(page.getByLabel('知识库范围说明')).toContainText('仅支持数据库内已收录的知识点');
  await expect(page.getByRole('heading',{name:/不止知道答案/})).toBeVisible();
  await page.screenshot({path:'test-results/home-desktop.png',fullPage:true,animations:'disabled'});
  await page.getByRole('textbox',{name:'输入问题'}).fill('密度为什么能大于1？');
  await page.getByRole('button',{name:'发送问题'}).click();
  await expect(page.getByText('概率密度可以大于 1。',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'点赞',exact:true}).click();
  await expect(page.getByText('已记录，可修改')).toBeVisible();
  await page.getByRole('button',{name:'点踩',exact:true}).click();
  await expect.poll(()=>votes.length).toBe(2);
  expect(votes.map(v=>v.score)).toEqual([1,-1]);expect(qaCalls).toBe(1);
  await page.getByRole('button',{name:/费曼练习/}).click();
  await expect(page.getByLabel('知识库范围说明')).toBeVisible();
  await page.getByRole('button',{name:'开始练习',exact:true}).click();
  await expect(page.getByText('为什么标准化时要除以标准差？')).toBeVisible();
  await page.getByRole('textbox',{name:/现在，讲给我听/}).fill('消除尺度影响');
  await page.getByRole('button',{name:/提交解释，看看反馈/}).click();
  await expect(page.getByText('已经抓住部分要点')).toBeVisible();
  await page.getByRole('button',{name:'点赞',exact:true}).click();
  await expect.poll(()=>votes.length).toBe(3);expect(votes[2].record_id).toBe(202);expect(judgeCalls).toBe(1);
  await page.screenshot({path:'test-results/practice-desktop.png',fullPage:true,animations:'disabled'});
  await page.getByRole('combobox',{name:'选择主题'}).selectOption('指数分布：无记忆性');
  await expect(page.getByText('为什么标准化时要除以标准差？')).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:/知识问答/}).click();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'test-results/ask-mobile.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:/学习记录/}).click();
  await expect(page.getByRole('heading',{name:/每一次学习/})).toBeVisible();
  await expect(page.getByText('最近调用记录')).toBeVisible();
  await page.setViewportSize({width:1440,height:1000});
  await page.screenshot({path:'test-results/dashboard-desktop.png',fullPage:true,animations:'disabled'});
  expect(failures).toEqual([]);
});
