import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',workers:1,use:{
  baseURL:process.env.PLAYWRIGHT_BASE_URL||'http://127.0.0.1:8000',
  viewport:{width:1440,height:1000},
  launchOptions:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?
    {executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{},
},reporter:'list'});
