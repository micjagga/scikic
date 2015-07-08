#decides if the string entered is a truth or a false (probably not worth it as we're switching away from text-input)
def true_string(st):
    if st == None:
        return False
    if (st[0].upper()=='Y'): #yes,Yes,Yep,YEP,y,Y
        return True
    if (st[0].upper()=='T'): #True,true,T,t
        return True
    return False #false,False,F,Wrong,Nope,No,(correct)
