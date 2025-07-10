from user.models import Role

def run():
    names = ["assistant","manager","maintainer","security","technician"]
    for name in names:
        Role.objects.create(name=name,name_en=name,name_vi=name,name_zh_hant=name)