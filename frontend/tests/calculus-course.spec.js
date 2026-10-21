import {test, expect} from '@playwright/test';

test('高数问答说明与练习章节跟随课程切换', async ({page}) => {
  await page.route('**/api/chats', route => route.fulfill({json:[]}));
  await page.goto('/');
  await page.getByRole('combobox', {name:'选择学科'}).click();
  await page.getByRole('option', {name:'高等数学', exact:true}).click();
  await expect(page.getByLabel('知识库范围说明')).toContainText('48 条高数条目可用于问答与练习');
  await expect(page.getByText('基于高等数学知识库')).toBeVisible();
  await expect(page.getByText('数列有界为什么不一定收敛？')).toBeVisible();
  await page.getByRole('button', {name:/费曼练习/}).click();
  await expect(page.getByLabel('知识库范围说明')).toContainText('5 条数学分析扩展仅供问答');
  await expect(page.getByRole('combobox', {name:'选择章节'})).toContainText('函数与极限', {timeout:30000});
  await expect(page.getByRole('combobox', {name:'选择章节'})).not.toContainText('一元微分学');
  await expect(page.getByRole('combobox', {name:'选择主题'})).toContainText('第一节：映射与函数', {timeout:30000});
  await expect(page.getByRole('combobox', {name:'选择章节'})).not.toContainText('实数与点集');
  await page.getByRole('combobox', {name:'选择学科'}).click();
  await page.getByRole('option', {name:'概率论', exact:true}).click();
  await page.getByRole('button', {name:/知识问答/}).click();
  await expect(page.getByText('基于概率论知识库')).toBeVisible();
});

test('知识问答的对比表与绝对值公式正确渲染', async ({page}) => {
  await page.route('**/api/chats', route => route.fulfill({json:[]}));
  await page.route('**/api/qa', route => route.fulfill({json:{
    question:'比较连续与一致连续',
    answer:'## 总结对比\n|比较项目|连续|一致连续|\n|---|---|---|\n|条件|$|x-a|<\\delta$|$|x-y|<\\delta$|',
    course:'高等数学', sources:[], usage:null,
  }}));
  await page.goto('/');
  await page.getByRole('combobox', {name:'选择学科'}).click();
  await page.getByRole('option', {name:'高等数学', exact:true}).click();
  await page.getByRole('textbox', {name:'输入问题'}).fill('比较连续与一致连续');
  await page.getByRole('button', {name:'发送问题'}).click();
  await expect(page.locator('.answer-card table')).toBeVisible();
  await expect(page.locator('.answer-card table tr')).toHaveCount(2);
  await expect(page.locator('.answer-card table td').nth(1)).toContainText('x−a');
});
