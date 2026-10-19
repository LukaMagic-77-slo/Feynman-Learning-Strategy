import {test,expect} from '@playwright/test';

test('聊天标题、继续提问、切换、刷新恢复与手机历史入口',async({page})=>{
  const chats=new Map(),requests=[],failures=[];
  page.on('pageerror',e=>failures.push(e.message));
  await page.route('**/api/chats',route=>route.fulfill({json:[...chats].map(([chat_id,turns])=>({chat_id,title:turns[0].question,turns:turns.length,updated_at:new Date().toISOString()})).reverse()}));
  await page.route('**/api/chats/*/history',route=>{
    const id=new URL(route.request().url()).pathname.split('/')[3];
    return route.fulfill({json:chats.get(id)||[]});
  });
  await page.route('**/api/qa',route=>{
    const body=route.request().postDataJSON();requests.push(body);
    const turns=chats.get(body.chat_id)||[];
    const result={question:body.question,answer:'回答：'+body.question,chat_id:body.chat_id,
      history_id:requests.length,record_id:100+requests.length,sources:[],usage:null};
    chats.set(body.chat_id,[...turns,result]);
    return route.fulfill({json:result});
  });
  await page.route('**/api/feedback',route=>route.fulfill({json:{id:1}}));
  await page.goto('/');
  const input=page.getByRole('textbox',{name:'输入问题'});
  await expect(input).toBeEnabled();
  await input.fill('正态分布是什么？');
  await page.getByRole('button',{name:'发送问题'}).click();
  await expect(page.getByRole('button',{name:'打开聊天：正态分布是什么？'})).toBeVisible();
  const firstId=requests[0].chat_id;
  await input.fill('怎样标准化？');
  await page.getByRole('button',{name:'发送问题'}).click();
  await expect(page.getByText('回答：怎样标准化？',{exact:true})).toBeVisible();
  expect(requests[1].chat_id).toBe(firstId);
  await expect(page.getByRole('button',{name:'打开聊天：正态分布是什么？'})).toHaveCount(1);
  await expect(page.getByRole('button',{name:'打开聊天：怎样标准化？'})).toHaveCount(0);
  await page.getByRole('button',{name:'新建聊天',exact:true}).click();
  await expect(page.getByText('回答：怎样标准化？',{exact:true})).toHaveCount(0);
  await input.fill('指数分布是什么？');
  await page.getByRole('button',{name:'发送问题'}).click();
  await expect(page.getByRole('button',{name:'打开聊天：指数分布是什么？'})).toBeVisible();
  expect(requests[2].chat_id).not.toBe(firstId);
  await page.getByRole('button',{name:'打开聊天：正态分布是什么？'}).click();
  await expect(page.getByText('回答：怎样标准化？',{exact:true})).toBeVisible();
  await expect(page.getByText('回答：指数分布是什么？',{exact:true})).toHaveCount(0);
  await page.reload();
  await expect(page.getByText('回答：正态分布是什么？',{exact:true})).toBeVisible();
  await expect(page.getByText('回答：怎样标准化？',{exact:true})).toBeVisible();
  expect(requests).toHaveLength(3);
  await page.screenshot({path:'test-results/history-desktop.png',fullPage:true,animations:'disabled'});
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'打开聊天历史',exact:true}).click();
  await expect(page.getByRole('button',{name:'打开聊天：指数分布是什么？'})).toBeVisible();
  await page.screenshot({path:'test-results/history-mobile.png',fullPage:true,animations:'disabled'});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('button',{name:'打开聊天：指数分布是什么？'}).click();
  await expect(page.getByText('回答：指数分布是什么？',{exact:true})).toBeVisible();
  expect(failures).toEqual([]);
});
