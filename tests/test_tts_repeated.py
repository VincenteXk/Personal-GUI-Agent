"""TTS 重复调用测试 - 验证多次TTS合成问题"""

import asyncio
import tempfile
import os
import time
import edge_tts
from playsound import playsound


def test_tts_single_asyncio_run():
    """测试1: 多次 asyncio.run() 调用"""
    print("\n" + "=" * 50)
    print("测试1: 多次 asyncio.run() 方式（当前voice.py的实现）")
    print("=" * 50)
    
    texts = [
        "这是第一段测试语音。",
        "这是第二段测试语音。",
        "这是第三段测试语音。",
        "这是第四段测试语音。",
        "这是第五段测试语音。",
    ]
    
    for i, text in enumerate(texts, 1):
        try:
            print(f"\n[{i}/5] 合成中: {text}")
            start_time = time.time()
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # 模拟当前voice.py的实现方式
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
            asyncio.run(communicate.save(temp_path))
            
            tts_time = time.time() - start_time
            print(f"  ✅ TTS耗时: {tts_time:.2f}秒")
            
            # 播放（可以注释掉加快测试）
            # playsound(temp_path, block=True)
            
            # 清理
            os.remove(temp_path)
            
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n测试1完成")


async def tts_async(text: str, temp_path: str):
    """异步TTS合成"""
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
    await communicate.save(temp_path)


def test_tts_shared_event_loop():
    """测试2: 共享事件循环方式（推荐修复方案）"""
    print("\n" + "=" * 50)
    print("测试2: 共享事件循环方式（推荐修复方案）")
    print("=" * 50)
    
    texts = [
        "这是第一段测试语音。",
        "这是第二段测试语音。",
        "这是第三段测试语音。",
        "这是第四段测试语音。",
        "这是第五段测试语音。",
    ]
    
    async def run_all():
        for i, text in enumerate(texts, 1):
            try:
                print(f"\n[{i}/5] 合成中: {text}")
                start_time = time.time()
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_path = temp_file.name
                
                await tts_async(text, temp_path)
                
                tts_time = time.time() - start_time
                print(f"  ✅ TTS耗时: {tts_time:.2f}秒")
                
                # 清理
                os.remove(temp_path)
                
            except Exception as e:
                print(f"  ❌ 失败: {e}")
                import traceback
                traceback.print_exc()
    
    asyncio.run(run_all())
    print("\n测试2完成")


def test_tts_sequential_rapid():
    """测试3: 快速连续调用（模拟实际场景）"""
    print("\n" + "=" * 50)
    print("测试3: 快速连续调用（无间隔）")
    print("=" * 50)
    
    texts = [
        "第一段。",
        "第二段。",
        "第三段。",
        "第四段。",
        "第五段。",
        "第六段。",
        "第七段。",
        "第八段。",
    ]
    
    success_count = 0
    fail_count = 0
    
    for i, text in enumerate(texts, 1):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
            
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
            asyncio.run(communicate.save(temp_path))
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                print(f"  [{i}] ✅ 成功")
                success_count += 1
            else:
                print(f"  [{i}] ⚠️ 文件为空")
                fail_count += 1
            
            os.remove(temp_path)
            
        except Exception as e:
            print(f"  [{i}] ❌ 失败: {e}")
            fail_count += 1
    
    print(f"\n结果: 成功 {success_count}/{len(texts)}, 失败 {fail_count}/{len(texts)}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔊 TTS 重复调用测试")
    print("=" * 70)
    
    # 运行测试
    test_tts_single_asyncio_run()
    test_tts_shared_event_loop()
    test_tts_sequential_rapid()
    
    print("\n" + "=" * 70)
    print("📊 测试完成")
    print("=" * 70)
