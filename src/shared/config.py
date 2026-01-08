"""Shared configuration for app package mappings across projects."""

# 合并Open-AutoGLM和behavior_analyzer中的应用包名映射
# 去重并优先保留英文名称
APP_PACKAGE_MAPPINGS = {
    "com.tencent.mm": "微信",
    "com.tencent.mobileqq": "QQ",
    "com.sina.weibo": "微博",
    "com.taobao.taobao": "淘宝",
    "com.jingdong.app.mall": "京东",
    "com.xunmeng.pinduoduo": "拼多多",
    "com.xingin.xhs": "小红书",
    "com.douban.frodo": "豆瓣",
    "com.zhihu.android": "知乎",
    "com.autonavi.minimap": "高德地图",
    "com.baidu.BaiduMap": "百度地图",
    "com.sankuai.meituan": "美团",
    "com.dianping.v1": "大众点评",
    "me.ele": "饿了么",
    "com.yek.android.kfc.activitys": "肯德基",
    "ctrip.android.view": "携程",
    "com.MobileTicket": "铁路12306",
    "com.Qunar": "去哪儿",
    "com.sdu.didi.psnger": "滴滴出行",
    "tv.danmaku.bili": "bilibili",
    "com.ss.android.ugc.aweme": "抖音",
    "com.smile.gifmaker": "快手",
    "com.tencent.qqlive": "腾讯视频",
    "com.qiyi.video": "爱奇艺",
    "com.youku.phone": "优酷视频",
    "com.hunantv.imgo.activity": "芒果TV",
    "com.phoenix.read": "红果短剧",
    "com.netease.cloudmusic": "网易云音乐",
    "com.tencent.qqmusic": "QQ音乐",
    "com.luna.music": "汽水音乐",
    "com.ximalaya.ting.android": "喜马拉雅",
    "com.dragon.read": "番茄小说",
    "com.kmxs.reader": "七猫免费小说",
    "com.ss.android.lark": "飞书",
    "com.tencent.androidqqmail": "QQ邮箱",
    "com.larus.nova": "豆包",
    "com.gotokeep.keep": "keep",
    "com.lingan.seeyou": "美柚",
    "com.tencent.news": "腾讯新闻",
    "com.ss.android.article.news": "今日头条",
    "com.lianjia.beike": "贝壳找房",
    "com.anjuke.android.app": "安居客",
    "com.hexin.plat.android": "同花顺",
    "com.miHoYo.hkrpg": "星穹铁道",
    "com.papegames.lysk.cn": "恋与深空",
    "com.android.settings": "AndroidSystemSettings",
    "com.android.soundrecorder": "AudioRecorder",
    "com.rammigsoftware.bluecoins": "Bluecoins",
    "com.flauschcode.broccoli": "Broccoli",
    "com.booking": "Booking.com",
    "com.android.chrome": "Chrome",  # 优先使用英文名称
    "com.android.deskclock": "Clock",
    "com.android.contacts": "Contacts",
    "com.duolingo": "Duolingo",
    "com.expedia.bookings": "Expedia",
    "com.android.fileexplorer": "Files",
    "com.google.android.gm": "Gmail",
    "com.google.android.apps.nbu.files": "GoogleFiles",
    "com.google.android.calendar": "GoogleCalendar",
    "com.google.android.apps.dynamite": "GoogleChat",
    "com.google.android.deskclock": "GoogleClock",
    "com.google.android.contacts": "GoogleContacts",
    "com.google.android.apps.docs.editors.docs": "GoogleDocs",
    "com.google.android.apps.docs": "GoogleDrive",
    "com.google.android.apps.fitness": "GoogleFit",
    "com.google.android.keep": "GoogleKeep",
    "com.google.android.apps.maps": "GoogleMaps",
    "com.google.android.apps.books": "GooglePlayBooks",
    "com.android.vending": "GooglePlayStore",
    "com.google.android.apps.docs.editors.slides": "GoogleSlides",
    "com.google.android.apps.tasks": "GoogleTasks",
    "net.cozic.joplin": "Joplin",
    "com.mcdonalds.app": "McDonald",
    "net.osmand": "Osmand",
    "com.Project100Pi.themusicplayer": "PiMusicPlayer",
    "com.quora.android": "Quora",
    "com.reddit.frontpage": "Reddit",
    "code.name.monkey.retromusic": "RetroMusic",
    "com.scientificcalculatorplus.simplecalculator.basiccalculator.mathcalc": "SimpleCalendarPro",
    "com.simplemobiletools.smsmessenger": "SimpleSMSMessenger",
    "org.telegram.messenger": "Telegram",
    "com.einnovation.temu": "temu",
    "com.zhiliaoapp.musically": "Tiktok",
    "com.twitter.android": "Twitter",
    "org.videolan.vlc": "VLC",
    "com.whatsapp": "Whatsapp",
    "com.tmall.wireless": "天猫",
    "com.alibaba.android.rimet": "钉钉",
    "com.google.android.apps.nexuslauncher": "桌面",
    "com.android.launcher3": "桌面",
    "com.huawei.android.launcher": "桌面",
    "com.sec.android.app.launcher": "桌面",
    "com.miui.home": "桌面",
    "com.oppo.launcher": "桌面"
}

# 反向映射：从应用名称到包名
APP_NAME_TO_PACKAGE = {}
for package, name in APP_PACKAGE_MAPPINGS.items():
    # 如果应用名称不在反向映射中，添加映射
    if name not in APP_NAME_TO_PACKAGE:
        APP_NAME_TO_PACKAGE[name] = package

def get_app_name_from_package(package_name: str) -> str:
    """
    根据包名获取应用名称
    
    Args:
        package_name: 应用包名
        
    Returns:
        对应的应用名称，如果找不到则返回原始包名
    """
    return APP_PACKAGE_MAPPINGS.get(package_name, package_name)


def get_package_from_app_name(app_name: str) -> str | None:
    """
    根据应用名称获取包名
    
    Args:
        app_name: 应用名称
        
    Returns:
        对应的包名，如果找不到则返回None
    """
    return APP_NAME_TO_PACKAGE.get(app_name)