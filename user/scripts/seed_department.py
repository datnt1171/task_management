from user.models import Department

def run():
    names = ["QL","QT","TV","TT","PM","KP","KT","KHO","SX","KTC","KTW","KVN"]
    for name in names:
        Department.objects.create(name=name,name_en=name,name_vi=name,name_zh_hant=name)
