"""模拟 OpenAI 协议的本地服务（仅用于自检，返回满分答案）"""
import json
import re
import sys
import time

sys.path.insert(0, ".")

from fastapi import FastAPI, Request
from app import database as db

app = FastAPI()

GOOD_CODE = {
    "FizzBuzz": '```python\ndef solution(n):\n    out=[]\n    for i in range(1,n+1):\n        if i%15==0: out.append("FizzBuzz")\n        elif i%3==0: out.append("Fizz")\n        elif i%5==0: out.append("Buzz")\n        else: out.append(str(i))\n    return out\n```',
    "回文判断": '```python\ndef solution(s):\n    return s == s[::-1]\n```',
    "两数之和": '```python\ndef solution(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i]+nums[j]==target:\n                return [i,j]\n```',
    "反转单词顺序": '```python\ndef solution(s):\n    return " ".join(s.split()[::-1])\n```',
    "阶乘": '```python\ndef solution(n):\n    return 1 if n==0 else n*solution(n-1)\n```',
    "斐波那契": '```python\ndef solution(n):\n    a,b=0,1\n    for _ in range(n):\n        a,b=b,a+b\n    return a\n```',
    "合并区间": '```python\ndef solution(intervals):\n    intervals.sort(key=lambda x: x[0])\n    out = []\n    for s, e in intervals:\n        if not out or out[-1][1] < s:\n            out.append([s, e])\n        else:\n            out[-1][1] = max(out[-1][1], e)\n    return out\n```',
    "接雨水": '```python\ndef solution(height):\n    left, right = 0, len(height) - 1\n    lm = rm = total = 0\n    while left < right:\n        if height[left] < height[right]:\n            lm = max(lm, height[left])\n            total += lm - height[left]\n            left += 1\n        else:\n            rm = max(rm, height[right])\n            total += rm - height[right]\n            right -= 1\n    return total\n```',
    "最长回文子串": '```python\ndef solution(s):\n    best = ""\n    for i in range(len(s)):\n        for l, r in ((i, i), (i, i + 1)):\n            while l >= 0 and r < len(s) and s[l] == s[r]:\n                l -= 1; r += 1\n            if r - l - 1 > len(best):\n                best = s[l + 1:r]\n    return best\n```',
    "N皇后计数": '```python\ndef solution(n):\n    cols, d1, d2 = set(), set(), set()\n    def dfs(row):\n        if row == n:\n            return 1\n        cnt = 0\n        for col in range(n):\n            if col in cols or (row - col) in d1 or (row + col) in d2:\n                continue\n            cols.add(col); d1.add(row - col); d2.add(row + col)\n            cnt += dfs(row + 1)\n            cols.remove(col); d1.remove(row - col); d2.remove(row + col)\n        return cnt\n    return dfs(0)\n```',
    "无重复字符的最长子串": '```python\ndef solution(s):\n    seen = {}\n    left = best = 0\n    for right, ch in enumerate(s):\n        if ch in seen and seen[ch] >= left:\n            left = seen[ch] + 1\n        seen[ch] = right\n        best = max(best, right - left + 1)\n    return best\n```',
    "岛屿数量": '```python\ndef solution(grid):\n    if not grid:\n        return 0\n    rows, cols = len(grid), len(grid[0])\n    def dfs(r, c):\n        if r < 0 or c < 0 or r >= rows or c >= cols or grid[r][c] != "1":\n            return\n        grid[r][c] = "0"\n        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):\n            dfs(r + dr, c + dc)\n    cnt = 0\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] == "1":\n                cnt += 1\n                dfs(r, c)\n    return cnt\n```',
    "编辑距离": '```python\ndef solution(word1, word2):\n    m, n = len(word1), len(word2)\n    dp = [[0] * (n + 1) for _ in range(m + 1)]\n    for i in range(m + 1):\n        dp[i][0] = i\n    for j in range(n + 1):\n        dp[0][j] = j\n    for i in range(1, m + 1):\n        for j in range(1, n + 1):\n            if word1[i-1] == word2[j-1]:\n                dp[i][j] = dp[i-1][j-1]\n            else:\n                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])\n    return dp[m][n]\n```',
}


def find_question(prompt: str):
    if not prompt:
        return None
    for q in db.query("SELECT * FROM questions ORDER BY id"):
        if q["prompt"] and q["prompt"] in prompt:
            return q
    return None


GOOD_HTML = {
    "互动拍立得相机": """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background:#2b2b2b; font-family:sans-serif; }
  .camera { position:relative; width:340px; height:260px; background:linear-gradient(160deg,#e8e4dd,#b9b3a8); border-radius:22px; box-shadow:0 18px 40px rgba(0,0,0,.45), inset 0 2px 4px rgba(255,255,255,.6); padding:26px; }
  .lens { position:absolute; top:52px; left:50%; transform:translateX(-50%); width:96px; height:96px; border-radius:50%; background:radial-gradient(circle at 32% 30%, #9fd4ff, #1a2b45 55%, #05080f 90%); box-shadow:0 0 0 10px #3a3a3a, 0 0 0 14px #cfc9bd, inset 0 4px 10px rgba(255,255,255,.25); }
  #shutter { position:absolute; top:30px; right:34px; width:64px; height:28px; border-radius:14px; border:none; background:linear-gradient(#ff7a6b,#c43d2e); color:#fff; font-weight:bold; letter-spacing:2px; cursor:pointer; box-shadow:0 4px 8px rgba(0,0,0,.35); }
  #shutter:active { transform:translateY(2px); }
  .slot { position:absolute; bottom:20px; left:50%; transform:translateX(-50%); width:270px; height:12px; background:#111; border-radius:6px; box-shadow:inset 0 3px 6px rgba(0,0,0,.8); }
  .photo { position:absolute; bottom:36px; left:50%; width:150px; height:120px; background:#fff; padding:10px 10px 34px; border-radius:4px; box-shadow:0 8px 16px rgba(0,0,0,.4); animation:out .8s ease-out; }
  .photo .img { width:100%; height:100%; background:linear-gradient(135deg, hsl(var(--h1)), hsl(var(--h2))); }
  @keyframes out { from { transform:translate(-50%,26px) rotate(-2deg); opacity:0 } to { transform:translate(-50%,0) rotate(1deg); opacity:1 } }
</style>
</head>
<body>
  <div class="camera">
    <div class="lens"></div>
    <button id="shutter">快门</button>
    <div class="slot"></div>
  </div>
  <script>
    const btn = document.getElementById('shutter');
    let n = 0;
    btn.addEventListener('click', () => {
      const p = document.createElement('div');
      p.className = 'photo';
      const h1 = Math.floor(Math.random()*360), h2 = (h1 + 40) % 360;
      p.innerHTML = '<div class="img" style="--h1:'+h1+';--h2:'+h2+'"></div>';
      document.querySelector('.camera').appendChild(p);
      if (++n > 3) document.querySelectorAll('.photo')[0].remove();
    });
  </script>
</body>
</html>""",
    "macOS 风格网页操作系统": """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { margin:0; overflow:hidden; font-family:"Segoe UI",sans-serif; }
  .desktop { position:relative; width:100vw; height:100vh; background:linear-gradient(135deg,#3a7bd5,#2a5298 55%,#6a3093); }
  .menubar { position:absolute; top:0; left:0; right:0; height:28px; background:rgba(245,245,245,.85); backdrop-filter:blur(12px); display:flex; align-items:center; padding:0 12px; font-size:13px; color:#333; z-index:9; }
  .dock { position:absolute; bottom:10px; left:50%; transform:translateX(-50%); display:flex; gap:10px; padding:8px 14px; background:rgba(255,255,255,.25); backdrop-filter:blur(20px); border-radius:18px; z-index:10; }
  .app-icon { width:48px; height:48px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:22px; cursor:pointer; transition:.15s; color:#fff; }
  .app-icon:hover { transform:scale(1.15); }
  .window { position:absolute; width:360px; height:240px; background:#fff; border-radius:10px; box-shadow:0 16px 40px rgba(0,0,0,.4); overflow:hidden; display:flex; flex-direction:column; }
  .titlebar { height:28px; background:linear-gradient(#e8e8e8,#d0d0d0); display:flex; align-items:center; padding:0 10px; font-size:12px; }
  .close { margin-left:auto; width:12px; height:12px; border-radius:50%; background:#ff5f57; cursor:pointer; }
  .content { flex:1; padding:8px; overflow:auto; }
  textarea { width:100%; height:100%; border:none; outline:none; resize:none; font-family:Consolas,monospace; }
  canvas { border:1px solid #ddd; }
  .term { background:#111; color:#0f0; font-family:Consolas,monospace; padding:6px; height:100%; }
</style>
</head>
<body>
  <div class="desktop" id="desktop">
    <div class="menubar"> Finder  文件  编辑  显示  前往  窗口  帮助 </div>
    <div class="dock" id="dock">
      <div class="app-icon" data-app="editor" style="background:#1e90ff">✎</div>
      <div class="app-icon" data-app="terminal" style="background:#222">▸</div>
      <div class="app-icon" data-app="paint" style="background:#ff6b81">🎨</div>
      <div class="app-icon" data-app="files" style="background:#4c9aff">🗂</div>
      <div class="app-icon" data-app="game" style="background:#8e44ad">🎮</div>
      <div class="app-icon" data-app="video" style="background:#e67e22">🎬</div>
      <div class="app-icon" data-app="code" style="background:#16a085">⌨</div>
      <div class="app-icon" data-app="python" style="background:#f1c40f;color:#333">Py</div>
    </div>
  </div>
  <script>
    const desktop = document.getElementById('desktop');
    let zi = 100;
    function openApp(name, title) {
      const w = document.createElement('div');
      w.className = 'window';
      w.style.left = (80 + Math.random()*160) + 'px';
      w.style.top = (60 + Math.random()*120) + 'px';
      w.style.zIndex = ++zi;
      w.innerHTML = '<div class="titlebar"><span>'+title+'</span><span class="close"></span></div><div class="content"></div>';
      const c = w.querySelector('.content');
      if (name === 'editor') c.innerHTML = '<textarea placeholder="开始输入…"></textarea>';
      else if (name === 'terminal') {
        c.className = 'term';
        c.innerHTML = 'macOS Terminal — 输入 help 试试<br>';
        const inp = document.createElement('input');
        inp.style.cssText = 'background:#111;color:#0f0;border:none;outline:none;font-family:Consolas,monospace;width:90%';
        c.appendChild(inp);
        inp.addEventListener('keydown', e => {
          if (e.key === 'Enter') {
            const out = document.createElement('div');
            out.textContent = inp.value === 'help' ? '可用命令: help, ls, echo' : 'command not found: ' + inp.value;
            c.insertBefore(out, inp); inp.value = '';
          }
        });
      } else if (name === 'paint') {
        c.innerHTML = '<canvas width="330" height="180"></canvas>';
        const cv = c.querySelector('canvas'), ctx = cv.getContext('2d');
        let down = false;
        cv.onmousedown = () => down = true;
        cv.onmouseup = () => down = false;
        cv.onmousemove = e => { if (down) { ctx.fillRect(e.offsetX, e.offsetY, 3, 3); } };
      } else if (name === 'python') {
        c.className = 'term';
        c.innerHTML = 'Python 3.11 (模拟) — 仅支持 print("...")<br>';
        const inp = document.createElement('input');
        inp.style.cssText = 'background:#111;color:#0f0;border:none;outline:none;font-family:Consolas,monospace;width:90%';
        c.appendChild(inp);
        inp.addEventListener('keydown', e => {
          if (e.key === 'Enter') {
            const m = inp.value.match(/^print\\(\\"([^\\"]*)\\"\\)$/);
            const out = document.createElement('div');
            out.textContent = m ? m[1] : 'SyntaxError: 仅支持 print("...")';
            c.insertBefore(out, inp); inp.value = '';
          }
        });
      } else {
        c.innerHTML = '<p>'+title+' 窗口（模拟）</p>';
      }
      desktop.appendChild(w);
      w.querySelector('.close').onclick = () => w.remove();
      w.onmousedown = () => { w.style.zIndex = ++zi; };
      const bar = w.querySelector('.titlebar');
      bar.onmousedown = e => {
        const ox = e.clientX - w.offsetLeft, oy = e.clientY - w.offsetTop;
        const mv = ev => { w.style.left = (ev.clientX - ox) + 'px'; w.style.top = (ev.clientY - oy) + 'px'; };
        document.addEventListener('mousemove', mv);
        document.addEventListener('mouseup', () => document.removeEventListener('mousemove', mv), {once:true});
      };
    }
    document.querySelectorAll('.app-icon').forEach(icon => {
      icon.addEventListener('click', () => openApp(icon.dataset.app, icon.textContent.trim()));
    });
  </script>
</body>
</html>""",
    "科幻飞船驾驶舱 HUD": """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { margin:0; overflow:hidden; background:#000; }
  #hud { position:relative; width:100vw; height:100vh; }
  #bg { position:absolute; inset:0; }
  #glass { position:absolute; inset:0; pointer-events:none; background:linear-gradient(115deg, rgba(120,200,255,.08), transparent 40%, rgba(160,230,255,.05)); }
  .reticle { position:absolute; left:50%; top:50%; width:90px; height:90px; margin:-45px 0 0 -45px; pointer-events:none; }
  .reticle::before { content:''; position:absolute; inset:0; border:2px solid rgba(80,220,255,.9); border-radius:50%; box-shadow:0 0 14px rgba(80,220,255,.5); }
  .reticle::after { content:''; position:absolute; left:50%; top:50%; width:6px; height:6px; margin:-3px 0 0 -3px; background:#7de8ff; border-radius:50%; }
  .ring { position:absolute; border:1px solid rgba(80,220,255,.45); border-radius:50%; pointer-events:none; }
  .ring1 { left:8%; top:10%; width:170px; height:170px; }
  .ring2 { right:8%; bottom:12%; width:200px; height:200px; }
  .ring3 { left:12%; bottom:14%; width:120px; height:120px; }
  .ring4 { right:10%; top:8%; width:150px; height:150px; }
  .ring5 { left:34%; top:4%; width:90px; height:90px; }
  .ring6 { right:30%; bottom:6%; width:110px; height:110px; }
  .sweep { position:absolute; width:50%; height:2px; background:linear-gradient(90deg, rgba(80,220,255,.7), transparent); transform-origin:left center; }
</style>
</head>
<body>
  <div id="hud">
    <canvas id="bg"></canvas>
    <div class="ring ring1"><div class="sweep" style="animation:spin 4s linear infinite"></div></div>
    <div class="ring ring2"></div><div class="ring ring3"></div><div class="ring ring4"></div>
    <div class="ring ring5"></div><div class="ring ring6"></div>
    <div class="reticle" id="reticle"></div>
    <div id="glass"></div>
  </div>
  <style> @keyframes spin { to { transform: rotate(360deg); } } </style>
  <script>
    const cv = document.getElementById('bg'), ctx = cv.getContext('2d');
    cv.width = innerWidth; cv.height = innerHeight;
    const stars = Array.from({length: 160}, () => ({x: Math.random()*innerWidth, y: Math.random()*innerHeight, r: Math.random()*1.6, s: Math.random()*0.15 + 0.03}));
    function loop() {
      ctx.fillStyle = '#02040a'; ctx.fillRect(0, 0, cv.width, cv.height);
      for (const st of stars) {
        st.y -= st.s;
        if (st.y < 0) { st.y = innerHeight; st.x = Math.random()*innerWidth; }
        ctx.fillStyle = 'rgba(200,230,255,' + (0.4 + st.r/3) + ')';
        ctx.fillRect(st.x, st.y, st.r, st.r);
      }
      requestAnimationFrame(loop);
    }
    loop();
    const reticle = document.getElementById('reticle');
    const rings = document.querySelectorAll('.ring');
    let mx = innerWidth/2, my = innerHeight/2;
    addEventListener('mousemove', e => {
      mx = e.clientX; my = e.clientY;
      reticle.style.transition = 'transform .05s ease-out';
      reticle.style.transform = 'translate(' + (mx - innerWidth/2) + 'px,' + (my - innerHeight/2) + 'px)';
      rings.forEach((r, i) => {
        r.style.transition = 'transform .35s ease-out';
        r.style.transform = 'translate(' + (mx - innerWidth/2) * 0.12 * (i % 3 + 1) / 3 + 'px,' + (my - innerHeight/2) * 0.12 * (i % 3 + 1) / 3 + 'px)';
      });
    });
  </script>
</body>
</html>""",
}


def craft_answer(prompt: str) -> str:
    if "pong" in prompt:
        return "pong"
    if "AI 评测裁判" in prompt:
        m = re.search(r"0 到 (\d+(?:\.\d+)?) 之间的数字", prompt)
        ms = float(m.group(1)) if m else 4.0
        return json.dumps({"score": ms, "reason": "回答准确完整，表达自然流畅。"}, ensure_ascii=False)
    q = find_question(prompt)
    if not q:
        return "模拟答案"
    atype = q["answer_type"]
    if atype == "choice":
        return json.loads(q["expected"])[0]
    if atype == "number":
        return "答案是 " + json.loads(q["expected"])[0]
    if atype == "code":
        return GOOD_CODE.get(q["title"], "```python\ndef solution():\n    return None\n```")
    if atype == "html":
        return "```html\n" + GOOD_HTML.get(q["title"], "<html><body>demo</body></html>") + "\n```"
    if q.get("judge"):
        return "这是一段温暖、真诚且得体的模拟回复，充分体现了共情与支持。"
    return json.loads(q["expected"])[0]


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    content = messages[-1].get("content") if messages else ""
    if isinstance(content, list):
        content = next((p.get("text", "") for p in content if p.get("type") == "text"), "")
    prompt = content or ""
    answer = craft_answer(prompt)
    resp = {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "mock"),
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }
    return resp


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
