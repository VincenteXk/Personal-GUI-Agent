"""播放测试 - 验证 playsound 多次调用问题"""

import tempfile
import os
import time
import asyncio
import edge_tts


def test_playsound_repeated():
    """测试1: playsound 多次调用（当前实现）"""
    from playsound import playsound
    
    print("\n" + "=" * 50)
    print("测试1: playsound 多次调用")
    print("=" * 50)
    
    texts = ["第一段。", "第二。", "第三。", "第四。", "第五。", "第六。"]
    
    for i, text in enumerate(texts, 1):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            
            # 合成
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
            asyncio.run(communicate.save(temp_path))
            print(f"[{i}] 合成完成，播放中...")
            
            # 播放
            start = time.time()
            playsound(temp_path, block=True)
            print(f"    ✅ 播放成功 ({time.time()-start:.2f}s)")
            
            os.remove(temp_path)
            
        except Exception as e:
            print(f"    ❌ 失败: {e}")


def test_pygame_mixer():
    """测试2: 使用 pygame.mixer（推荐替代方案）"""
    try:
        import pygame
        pygame.mixer.init()
    except ImportError:
        print("\n⚠️ pygame 未安装，跳过测试2")
        print("  安装命令: pip install pygame")
        return
    
    print("\n" + "=" * 50)
    print("测试2: pygame.mixer 多次调用")
    print("=" * 50)
    
    texts = ["第一段。", "第二。", "第三。", "第四。", "第五。", "第六。"]
    
    for i, text in enumerate(texts, 1):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            
            # 合成
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
            asyncio.run(communicate.save(temp_path))
            print(f"[{i}] 合成完成，播放中...")
            
            # 播放
            start = time.time()
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            print(f"    ✅ 播放成功 ({time.time()-start:.2f}s)")
            
            pygame.mixer.music.unload()  # 释放资源
            os.remove(temp_path)
            
        except Exception as e:
            print(f"    ❌ 失败: {e}")
    
    pygame.mixer.quit()


def test_pydub_simpleaudio():
    """测试3: 使用 pydub + simpleaudio"""
    try:
        from pydub import AudioSegment
        from pydub.playback import play
    except ImportError:
        print("\n⚠️ pydub/simpleaudio 未安装，跳过测试3")
        print("  安装命令: pip install pydub simpleaudio")
        return
    
    print("\n" + "=" * 50)
    print("测试3: pydub + simpleaudio（最稳定方案）")
    print("=" * 50)
    
    texts = ["第一段。", "第二。", "第三。", "第四。", "第五。", "第六。"]
    
    for i, text in enumerate(texts, 1):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            
            # 合成
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
            asyncio.run(communicate.save(temp_path))
            print(f"[{i}] 合成完成，播放中...")
            
            # 播放
            start = time.time()
            audio = AudioSegment.from_mp3(temp_path)
            play(audio)
            print(f"    ✅ 播放成功 ({time.time()-start:.2f}s)")
            
            os.remove(temp_path)
            
        except Exception as e:
            print(f"    ❌ 失败: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔊 音频播放测试 - 对比不同库")
    print("=" * 70)
    
    test_playsound_repeated()
    test_pygame_mixer()
    test_pydub_simpleaudio()
    
    print("\n" + "=" * 70)
    print("📊 测试完成")
    print("=" * 70)
