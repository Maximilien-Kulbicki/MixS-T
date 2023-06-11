from hashlib import new
from os import name
import copy
import math
import random
from tkinter import *


def getch():
    """Single char input, only works only on mac/linux/windows OS terminals"""
    try:
        import termios
        # POSIX system. Create and return a getch that manipulates the tty.
        import sys, tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        return msvcrt.getch().decode('utf-8')


def clavier(event):
    touche = event.keysym

    _actions = theGame()._actions

    if touche in _actions and not (touche == 'u') and not (touche == 'i'):
        theGame()._actions[touche](theGame().hero)
        theGame().floor.moveAllMonsters()
        theGame().turn += 1
        hunger(theGame().hero)

    elif touche.isdigit():  # pour l'usage des items, marche si l'entree est un nombre
        theGame()._actions['u'](theGame().hero, touche)
        theGame().floor.moveAllMonsters()
        theGame().turn += 1

    
    elif touche in theGame()._remove:
        val = theGame()._remove[f'{touche}']

        if val <= len(theGame().hero._inventory[0]) : # si la touche reenvoie une valeur atteignable
            try:
                theGame().hero.drop(theGame().hero._inventory[0][val]) #supprime l'element choisi de l'inventaire du heros
                theGame().turn += 1
            except Exception: # en cas d'erreur sur les indices de liste on ne fait rien
                pass

    elif touche == 'm':
        theGame()._actions['u'](theGame().hero, touche)


def sign(x):
    if x > 0:
        return 1
    return -1


class Coord(object):
    """Implementation of a map coordinate <x,y>"""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return '<' + str(self.x) + ',' + str(self.y) + '>'

    def __add__(self, other):
        return Coord(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Coord(self.x - other.x, self.y - other.y)

    def distance(self, other):
        return math.sqrt(math.pow(self.x - other.x, 2) + math.pow(self.y - other.y, 2))

    def direction(self, other):
        d = self - other  # différence entre self et other
        cos = d.x / self.distance(other)  # distance entre self et other

        if cos > 1 / math.sqrt(2):
            direction = Coord(-1, 0)
            return direction

        if cos == 1 / math.sqrt(2) and d.y < 0:
            direction = Coord(-1, 1)
            return direction

        if cos < -1 / math.sqrt(2):
            direction = Coord(1, 0)
            return direction

        if cos == -1 / math.sqrt(2) and d.y < 0:
            direction = Coord(1, 1)
            return direction

        elif d.y > 0:
            return Coord(0, -1)

        elif cos == 1 / math.sqrt(2) and d.y > 0:
            direction = Coord(-1, -1)
            return direction

        elif cos == -1 / math.sqrt(2) and d.y > 0:
            direction = Coord(1, -1)

        else:
            return Coord(0, 1)


class Element(object):
    """Base class for game elements.
        Has a name."""

    def __init__(self, name, abbrv=""):
        self.name = name
        if abbrv == "":
            abbrv = name[0]
        self.abbrv = abbrv

    def __repr__(self):
        return self.abbrv

    def description(self):
        """Description of the element"""
        return "<" + self.name + ">"

    def meet(self, hero):
        """Makes the hero meet an element. The hero takes the element."""
        raise NotImplementedError('Not implemented yet')
        # hero.take(self)
        # return True


class Equipment(Element):
    """Equipment to help the hero in his adventure"""

    def __init__(self, name, abbrv="", usage=None, price=0):
        super().__init__(name, abbrv)  # super() fait ref a la classe mere
        self.usage = usage  # usage est une fonction lambda
        self.price = price

    def meet(self, hero):
        """The hero takes an element"""
        if isinstance(hero, Hero):
            if self.name == "gold":
                hero.takeg(self)
                theGame().addMessage(f"You picked up a {self.name}")
                return True
            else:
                if len(hero._inventory[0]) < 10:
                    hero.take(self)
                    theGame().addMessage(f"You picked up a {self.name}")
                    return True
        return False

    def use(self, creature):
        if self.usage != None:  # si usage est defini
            theGame().addMessage(f"The {creature.name} uses the {self.name}")
            return self.usage(creature)
        else:
            theGame().addMessage(f"The {self.name} is not usable")
            return False

    def drop(self, creature):
        theGame().addMessage(f"The {creature.name} dropped {self.name}")
        return True



class Creature(Element):
    """A creature that occupies the dungeon.
        Is an Element. Has hit points and strength."""

    def __init__(self, name, hp, abbrv="", strength=1, xpGain=0):
        Element.__init__(self, name, abbrv)
        self.hp = hp
        self.strength = strength
        self.xpGain = xpGain

    def description(self):
        """Description of the creature"""
        return Element.description(self) + "(" + str(self.hp) + ")"

    def meet(self, hero):
        """The creature is encountered by the hero.
            The hero hits the creature, if alive the creature strikes back."""
        if not(isinstance(self,Merchant) and not(isinstance(hero, Merchant))):
            self.hp -= hero.strength
            theGame().addMessage(f"The {hero.name} hits the {self.description()}")
            if self.hp > 0:
            # hero.hp -= self.strength
            # theGame().addMessage(f"The {self.name} hits the {hero.description()}")
                return False
            if isinstance(hero, Hero):
                hero.gainXp(self.xpGain)  # ajoute pt xp a heros lorsque mob meurt

        return True


class Hero(Creature):
    """The hero of the game.
        Is a creature. Has an inventory of elements. """

    def __init__(self, name="Hero", hp=10, abbrv="@", strength=2, level=1, xp=0, hpMax=10, sat=50,satM=50):
        Creature.__init__(self, name, hp, abbrv, strength)
        self._inventory = [[], []] # une sous liste pour les items et une sous liste pour les pièces

        self.level = level
        self.xp = xp
        self.hpMax = hpMax
        self.satiety = sat
        self.satietyMax = satM

    def description(self):
        """Description of the hero"""
        return Creature.description(self) #+ str(self._inventory)

    def take(self, elem):
        """The hero adds the element to its inventory"""
        if not (isinstance(elem, Equipment)):
            raise TypeError('Not a Equipment')
        self._inventory[0].append(elem)

    def takeg(self, elem):
        """The hero adds the gold to its inventory"""
        if not (isinstance(elem, Equipment)):
            raise TypeError('Not a Equipment')
        self._inventory[1].append(elem)

    def fullDescription(self):
        """Describes the hero. Shows all elements in inventory"""
        des = []
        for att in self.__dict__:
            if str(att)[0] != "_" and not (str(att) in ['photo', 'abbrv',
                                                        'hpMax']):  # si ce n'est pas un attribut protégé ou un attribut que l'on ne souhaite pas montrer 
                des.append("> " + str(att) + " : " + str(getattr(self, att)))  # on rajoute nom attribut puis valeur

        l = [x.name for x in self._inventory[0]]
        g = len(self._inventory[1])
        des.append("> INVENTORY : " + str(l))  # liste contenant tous les elem de description
        des.append("> gold : " + str(g))
        res = ""
        for i in des:
            res += i + "\n"
        return res

    def use(self, item):
        """Uses item"""

        if not (isinstance(item, Equipment)):  # si l'item n'est pas un item
            #raise TypeError("Not an equipment")
            theGame().addMessage("Not an item")
            return 
        if not (item in self._inventory[0]):  # si l'item n'est pas dans l'inventaire
            #raise ValueError("Not in inventory")
            theGame().addMessage("Not in inventory")
            return

        if item.use(self):  # si use renvoie vrai
            self._inventory[0].remove(item)

    def drop(self, item):
        """Drops an  item"""
        if not (isinstance(item, Equipment)):  # si l'item n'est pas un item
            raise TypeError("Not an equipment")
        if not (item in self._inventory[0]):  # si l'item n'est pas dans l'inventaire
            raise ValueError("Not in inventory")

        if item.drop(self):  # si use renvoie vrai
            self._inventory[0].remove(item)

    def gainXp(self, xpGain):
        """Adds the xp"""
        if xpGain + self.xp < (self.level * 5):  # si la somme des xp est inf a 10*level
            self.xp += xpGain
            theGame().addMessage(f"You won {xpGain} experience point(s)")
            return True
        self.levelUp(xpGain)
        return True

    def levelUp(self, xpGain):
        """Levels up the hero"""
        xpAbove = xpGain + self.xp - (self.level * 5)  # on calcule les pt d'xp au dessus de l'xp max
        self.xp = xpAbove
        self.level += 1  # on augmente de niveau

        if self.level % 2 == 0:
            self.strength += 1

        if self.level % 2 != 0:
            self.hpMax += 1

        if self.hp < self.hpMax:
            self.hp = self.hpMax

        if self.satiety < 40:  
            self.satiety += 10

        theGame().addMessage("You gained a level")

        return True



class Merchant(Creature):
    """A creature that sells goods to the hero. Can die from monster hits"""
    def __init__(self, name="Merchant", hp=100, abbrv="$",strength=0,items=None):
        Creature.__init__(self,name,hp,abbrv,strength)
        if items is None:
            items = []
        self.items =items

        self.stock() #on fourni les items au marchand
    

    def stock(self):
        """Creates a stock for the merchant"""
        for i in range(5):
            a = theGame().randEquipment()
            if a.name !='gold' :
                self.items.append(a)
        

    def show(self,creature):
        """Shows the shop of the merchant"""
        res = "Hello stranger, what are you looking for ? \n BUY =>"

        for i in range(len(self.items)): # on ajoute la marchandise
            res+= f" '{i}': {self.items[i].name}({self.items[i].price}g) "
        res+='\n'

        inv = creature._inventory[0]
        m=''
        for i in range(len(inv)): # ajout des objets a racheter
            m += f"'{i+len(self.items)}': {inv[i].name}({inv[i].price}g) "
        res += f' SELL => {m}'

        res +='\n' # ajout sortie
        res += f" 'm' => EXIT"
    
        return res
    
    def changeEntry(self):
        """Redirects the num entries for the shop"""
        exchange(theGame()._actions, theGame()._merchant)

    def meet(self,creature):
        if isinstance(creature, Hero): # si heros, alors on peut vendre
            self.changeEntry() #ready to pickup the hero's input
            theGame().addMessage(self.show(creature)) #on ajoute le message en montrant vente et achat
            
            
    def discussion(self, creature, key):
        """Does a different actions depending on the input"""

        if  key.isdigit() and int(key) < len(self.items): #si la clé est pour les items
            self.buy(creature, int(key))

        elif key.isdigit() and int(key) >= len(self.items): #si on selectionne SELL
            self.sell(creature, key)

        elif key == 'm' : #si on veut quitter
            self.exit()

        else:
            theGame().addMessage('Try again...')
            theGame().addMessage(self.show(creature)) 

    def buy(self,creature,key):
        """Buys an element and adds it to the creature's inventory"""
        gold = len(creature._inventory[1]) #the hero's gold
        obj = self.items[key] #objet choisi

        if len(creature._inventory) < 10 and gold >= obj.price : #si on peut payer
            creature.take(self.items[key])# adds the elem...
            self.items.pop(key)#removes the element from the shop 
            del creature._inventory[1][-obj.price:] # on debite la creature 
            theGame().addMessage(f'You bought a {obj.name} for {obj.price} gold(s)')
        theGame().addMessage(self.show(creature))
        
    def sell(self,creature,key):
        newKey = int(key)-len(self.items)

        obj = creature._inventory[0][newKey]
        for i in range(obj.price):
            creature.takeg(theGame().equipments[0][1]) # on donne l'or au heros
            
        del creature._inventory[0][int(newKey)]
        theGame().addMessage(self.show(creature))

    def exit(self):
        self.changeEntry()
        theGame().addMessage('See you soon... in another world')



class Room(object):
    """A rectangular room in the map"""

    def __init__(self, c1, c2):
        self.c1 = c1
        self.c2 = c2

    def __repr__(self):
        return "[" + str(self.c1) + ", " + str(self.c2) + "]"

    def __contains__(self, coord):
        return self.c1.x <= coord.x <= self.c2.x and self.c1.y <= coord.y <= self.c2.y

    def intersect(self, other):
        """Test if the room has an intersection with another room"""
        sc3 = Coord(self.c2.x, self.c1.y)
        sc4 = Coord(self.c1.x, self.c2.y)
        return self.c1 in other or self.c2 in other or sc3 in other or sc4 in other or other.c1 in self

    def center(self):
        """Returns the coordinates of the room center"""
        return Coord((self.c1.x + self.c2.x) // 2, (self.c1.y + self.c2.y) // 2)

    def randCoord(self):
        x1 = random.randint(self.c1.x, self.c2.x)
        y1 = random.randint(self.c1.y, self.c2.y)
        return Coord(x1, y1)

    def randEmptyCoord(self, m):
        c = self.randCoord()
        while c == self.center() or m.get(c) != m.ground:
            c = self.randCoord()
        return c

    def decorate(self, m):
        """Puts an equipment and a creature at random coords"""
        c1 = self.randEmptyCoord(m)  # adding random equimpent to random empty cell
        eq = theGame().randEquipment()
        m.put(c1, eq)

        c2 = self.randEmptyCoord(m)  # adding random creature to random empty cell
        cr = theGame().randMonster()
        m.put(c2, cr)


class Stairs(Element):
    """Stairs to change map, is an element"""

    def __init__(self, name, abbrv=""):
        Element.__init__(self, name, abbrv="")

    def meet(self, hero):

        if isinstance(hero, Hero):

            if self.name == 'upStairs':
                if theGame().gameLevel < len(theGame().listMap):
                    theGame().gameLevel += 1
                    theGame().floor = theGame().listMap[theGame().gameLevel]  # on a changé la map

                return False

            elif self.name == 'downStairs':
                if theGame().gameLevel > 0:
                    theGame().gameLevel -= 1
                    theGame().floor = theGame().listMap[theGame().gameLevel]

                return False
            else:
                return False
        else:
            return False


class Map(object):
    """A map of a game floor.
        Contains game elements."""

    ground = '.'  # A walkable ground cell

    dir = {'z': Coord(0, -1),
           's': Coord(0, 1),
           'd': Coord(1, 0),
           'q': Coord(-1, 0)}  # four direction user keys

    empty = ' '  # A non walkable cell

    def __init__(self, size=20, hero=None, merchant=None):
        self._mat = []
        self._elem = {}

        self.size = size

        for i in range(size):
            self._mat.append([Map.empty] * size)

        self._rooms = []
        self._roomsToReach = []
        self.generateRooms(7)
        self.reachAllRooms()

        if hero is None:
            hero = Hero()
        self.hero = hero
        self.put(self._rooms[0].center(), hero)

        for i in self._rooms:
            i.decorate(self)

        self.addStairs()
        
        if merchant is None:
            merchant = Merchant()
        self.merchant = merchant




    def checkCoord(self, c):
        """check if c is coord and in map"""
        if not (isinstance(c, Coord)):  # si c pas de type coord
            raise TypeError('Not a Coord')
        if not (c in self):  # si c pas dans map
            raise IndexError('Out of map coord')

    def checkElement(self, e):
        """check if e a Element"""
        if not (isinstance(e, Element)):
            raise TypeError('Not a Element')

    def addRoom(self, room):
        """Adds a room in the map."""
        self._roomsToReach.append(room)
        for y in range(room.c1.y, room.c2.y + 1):
            for x in range(room.c1.x, room.c2.x + 1):
                self._mat[y][x] = Map.ground

    def findRoom(self, coord):
        """If the coord belongs to a room, returns the room elsewhere returns False."""
        for r in self._roomsToReach:
            if coord in r:
                return r
        return False

    def intersectNone(self, room):
        """Tests if the room shall intersect any room already in the map."""
        for r in self._roomsToReach:
            if room.intersect(r):
                return False
        return True

    def dig(self, coord):
        """Puts a ground cell at the given coord.
            If the coord corresponds to a room, considers the room reached."""
        self._mat[coord.y][coord.x] = Map.ground
        r = self.findRoom(coord)
        if r:
            self._roomsToReach.remove(r)
            self._rooms.append(r)

    def corridor(self, cursor, end):
        """Digs a corridors from the coordinates cursor to the end, first vertically, then horizontally."""
        d = end - cursor
        self.dig(cursor)
        while cursor.y != end.y:
            cursor = cursor + Coord(0, sign(d.y))
            self.dig(cursor)
        while cursor.x != end.x:
            cursor = cursor + Coord(sign(d.x), 0)
            self.dig(cursor)

    def reach(self):
        """Makes more rooms reachable.
            Start from one random reached room, and dig a corridor to an unreached room."""
        roomA = random.choice(self._rooms)
        roomB = random.choice(self._roomsToReach)
        self.corridor(roomA.center(), roomB.center())

    def reachAllRooms(self):
        """Makes all rooms reachable.
            Start from the first room, repeats @reach until all rooms are reached."""
        self._rooms.append(self._roomsToReach.pop(0))
        while len(self._roomsToReach) > 0:
            self.reach()

    def randRoom(self):
        """A random room to be put on the map."""
        c1 = Coord(random.randint(0, len(self) - 3), random.randint(0, len(self) - 3))
        c2 = Coord(min(c1.x + random.randint(3, 8), len(self) - 1), min(c1.y + random.randint(3, 8), len(self) - 1))
        return Room(c1, c2)

    def generateRooms(self, n):
        """Generates n random rooms and adds them if non-intersecting."""
        for i in range(n):
            r = self.randRoom()
            if self.intersectNone(r):
                self.addRoom(r)

    def __len__(self):
        return len(self._mat)

    def __contains__(self, item):
        if isinstance(item, Coord):
            return 0 <= item.x < len(self) and 0 <= item.y < len(self)
        return item in self._elem

    def __repr__(self):
        s = ""
        for i in self._mat:
            for j in i:
                s += str(j)
            s += '\n'
        return s

    def get(self, c):
        """Returns the object present on the cell c"""
        self.checkCoord(c)  # on verifie coord
        return self._mat[c.y][c.x]

    def put(self, c, o):
        """Puts an element o on the cell c"""
        self.checkCoord(c)
        self.checkElement(o)

        if self._mat[c.y][c.x] != Map.ground:  # on devrait pas toucher a _mat
            raise ValueError('Incorrect cell')

        if o in self:
            raise KeyError('Already placed')

        self._mat[c.y][c.x] = o
        self._elem[o] = c

    def pos(self, o):
        """Returns the coordinates of an element in the map """
        self.checkElement(o)
        return self._elem[o]

    def rm(self, c):
        """Removes the element at the coordinates c"""

        del self._elem[self.get(c)]
        self._mat[c.y][c.x] = Map.ground

    def move(self, e, way):
        """Moves the element e in the direction way."""
        orig = self.pos(e)
        dest = orig + way
        if dest in self:
            if self.get(dest) == Map.ground:
                self._mat[orig.y][orig.x] = Map.ground
                self._mat[dest.y][dest.x] = e
                self._elem[e] = dest
            elif self.get(dest) != Map.empty and self.get(dest).meet(e) and self.get(dest) != self.hero:
                self.rm(dest)

    def moveAllMonsters(self):
        """Moves all monsters one by one only if the monster detects the hero"""
        for mt in self._elem:
            cdM = 0
            cdH = 0
            if isinstance(mt, Creature) and not (isinstance(mt, Hero) and not(isinstance(mt, Merchant))):  # si l'ele est purement Creature
                cdM = self._elem[mt]  # coord de monstre
                cdH = self._elem[self.hero]
                d = cdH.distance(cdM)  # distance entre hero et monstre
                direction = cdM.direction(cdH)  # direction de l'heros par rapport au monstre
                if d < 6:  # si la créture détecte le heros
                    self.move(mt, direction)

    def addStairs(self):
        """Adds stairs"""
        rdRoom1 = random.choice(self._rooms)  # salle random
        rdCoord1 = rdRoom1.randEmptyCoord(self)  # coord random

        downStair = Stairs(name='downStairs', abbrv='d')
        self.put(rdCoord1, downStair)

        rdRoom2 = random.choice(self._rooms)  # 2eme salle random
        rdCoord2 = rdRoom2.randEmptyCoord(self)  # coord random

        upStairs = Stairs(name='upStairs', abbrv='m')
        self.put(rdCoord2, upStairs)

    def addMerchant(self):
        rdRoom1 = random.choice(self._rooms)  # salle random
        rdCoord1 = rdRoom1.randEmptyCoord(self)  # coord random
        self.put(rdCoord1, self.merchant)


class Game(object):
    """Contains the game's mecanics"""
    equipments = {0: [Equipment("potion", "!", lambda creature: heal(creature), price=2),
                      Equipment("gold", "o"),
                      Equipment("food", "F", lambda creature: eatFood(creature), price=2)],
                  1: [Equipment("sword", price=3),
                      Equipment("bow", price=3),
                      Equipment("telepotion", "!", lambda creature: teleport(creature, True), price=3)],
                  2: [Equipment("chainmail", price=4)],
                  3: [Equipment("portoloin", "w", lambda creature: teleport(creature, False),price=5 )],
                  }

    monsters = {0: [Creature("Goblin", 4, xpGain=3),
                    Creature("Bat", 2, "W", xpGain=1)],
                1: [Creature("Ork", 6, strength=2, xpGain=5),
                    Creature("Blob", 10, xpGain=7)],
                5: [Creature("Dragon", 20, strength=3, xpGain=15)]}

    _actions = {'z': lambda hero: theGame().floor.move(hero, Coord(0, -1)),
                's': lambda hero: theGame().floor.move(hero, Coord(0, 1)),
                'q': lambda hero: theGame().floor.move(hero, Coord(-1, 0)),
                'd': lambda hero: theGame().floor.move(hero, Coord(1, 0)),
                'i': lambda hero: theGame().addMessage(hero.fullDescription()),
                'k': lambda hero: hero.__setattr__('hp', 0),
                ' ': lambda _: None,
                'u': lambda hero, key: hero.use(theGame().select(hero._inventory[0], key)),
                'f': lambda hero, key: hero.drop(theGame().select(hero._inventory[0], key)),
                'a': lambda hero: theGame().floor.move(hero, Coord(-1, -1)),
                'w': lambda hero: theGame().floor.move(hero, Coord(-1, 1)),
                'e': lambda hero: theGame().floor.move(hero, Coord(1, -1)),
                'x': lambda hero: theGame().floor.move(hero, Coord(1, 1)), 
                }

    _remove = { 'ampersand' : 0,
                'eacute' : 1,
                'quotedbl' : 2,
                'quoteright' : 3,
                'parenleft' : 4,
                'minus' : 5,
                'egrave' : 6,
                'underscore' : 7,
                'ccedilla' : 8,
                'agrave' : 9
    }

    _merchant = { 'u' : lambda hero, key : theGame().floor.merchant.discussion(hero, key)

    }
    def __init__(self, hero=None, merchant=None, level=1, floor=None, _message=None, gameLevel=0, listMap=[], turn=0):

        self.gameLevel = gameLevel
        self.level = level
        self.turn = turn  # compteur de tour

        if hero is None:
            hero = Hero()
        self.hero = hero

        self.merchant = merchant

        self.floor = floor
        self.listMap = listMap  # liste des maps

        if _message is None:
            _message = []
        self._message = _message

    def buildFloor(self):
        """Building a floor"""
        self.floor = Map(size=40, hero=theGame().hero)  # map d'indice gameLevel
        self.listMap.append(self.floor)  # on rajoute première map a listMap

    def createFloors(self):
        """Adds new floors"""
        newFloor = oneListMap()
        self.listMap += newFloor  # on rajoute les nouvelles map a listMap

    def addMessage(self, msg):
        """Adds a message in _message"""
        self._message.append(msg)

    def readMessages(self):
        """Reads messages"""
        if self._message == None:
            return []

        res = ""
        for i in self._message:
            res += str(i) + ". "
        self._message.clear()

        return res

    def randElement(self, collection):
        """Returns a random element of the collection"""
        x = random.expovariate(1 / self.level)  #
        ele = 0
        for i in collection:
            if i < x and ele < i:  # trouve le degré de rarete le plus elevé inf a x
                ele = i
        return copy.copy(random.choice(collection[ele]))

    def randEquipment(self):
        return self.randElement(Game.equipments)

    def randMonster(self):
        return self.randElement(Game.monsters)

    def select(self, l, choice):
        """Chooses an equipment in the list l"""

        res = [f'{l.index(x)}: {x.name}' for x in l]
        # theGame().addMessage(f"Choose item> {res}") # on affiche la liste
        #print(f"Choose item> {res}")  # on imprime choix dispo

        if choice.isdigit() and (int(choice) <= len(l) and int(choice) >= 0):  # si le choix est un nb et possible
            try:
                return l[int(choice)]  # on renvoie l'élement de la liste correspondant
            except Exception:
                return None
        else:
            return None


class Interface(object):

    def __init__(self, game=None):

        self.fenetre = Tk()

        if game == None:
            game = theGame()  # le jeu qu'on represente
        self.game = game

        self.m = self.game.floor  # la carte du jeu

        self.texture = {

            'upStairs': PhotoImage(file="stone_stairs_up.png"),
            'downStairs': PhotoImage(file="stone_stairs_down.png"),

            'Goblin': PhotoImage(file="goblin.png"),
            'Bat': PhotoImage(file="bat.png"),
            'Blob': PhotoImage(file="blob.png"),
            'Ork': PhotoImage(file="orc.png"),
            'Dragon': PhotoImage(file="dragon.png"),

            'potion': PhotoImage(file="potion_heal.png"),
            'telepotion' : PhotoImage(file='potion_teleport.png'),
            'portoloin': PhotoImage(file="portoloin.png"),
            'food': PhotoImage(file="beef_raw.png"),

            'gold': PhotoImage(file="gold.png"),
            'sword': PhotoImage(file="sword.png"),
            'bow': PhotoImage(file="bow.png"),
            'chainmail': PhotoImage(file="armor_iron.png"),

            'Hero': PhotoImage(file="Red_Knight.png"),
            'Merchant' : PhotoImage(file='merchant.png'),
            'PhotoHero' : PhotoImage(file='Red_Knight_big.png'),

            'Full heart' : PhotoImage(file='heart_full_1.png'), 
            'Empty heart' : PhotoImage(file='heart_empty_1.png'),

            'Full food' : PhotoImage(file='beef_raw_1.png'),
            'Empty food' : PhotoImage(file='bone_1.png'),

        }
        self.texture_1 = { # blue texture
            'chemin': [PhotoImage(file=("texturefloor3.1.png")),
                       PhotoImage(file=("texturefloor3.2.png")),
                       PhotoImage(file=("texturefloor3.png"))],
            'background': PhotoImage(file="back3.png"),

            'portoloin': PhotoImage(file="rod08.png"),

            'Goblin': PhotoImage(file="ufetubus.png"),
            'Bat': PhotoImage(file="azure_jelly.png"),
            'Blob': PhotoImage(file="very_ugly_thing3.png"),
            'Ork': PhotoImage(file="ugly_thing3.png"),
            'Dragon': PhotoImage(file="blue_death.png"), 

            'sword': PhotoImage(file="urand_plutonium.png"),
            'bow': PhotoImage(file="urand_storm_bow.png"),
            'chainmail': PhotoImage(file="shield1_elven.png"),

            'Hero': PhotoImage(file="as_blue.png"),
            'PhotoHero' : PhotoImage(file='as_blue_big.png'),
            'HeroName' : 'Space Man',
            'MapName' : 'Virtual Star'

        }

        self.texture_2 = {  # pink texture
            'chemin': [PhotoImage(file=("pink1.png")),
                       PhotoImage(file=("pink2.png"))],
            'background' : PhotoImage(file='back2.1.png'),
            
            'potion': PhotoImage(file="magenta.png"),
            'telepotion' : PhotoImage(file='pink.png'),
            'portoloin': PhotoImage(file="gem_glass.png"),


            'Goblin': PhotoImage(file="unseen_horror.png"),
            'Bat': PhotoImage(file="shining_eye.png"),
            'Blob': PhotoImage(file="acid_blob.png"),
            'Ork': PhotoImage(file="ugly_thing4.png"),
            'Dragon': PhotoImage(file="mottled_dragon.png"),

            'sword': PhotoImage(file="demon_blade.png"),
            'bow': PhotoImage(file="blowgun1.png"),
            'chainmail': PhotoImage(file="shield2_kite.png"),

            'Hero': PhotoImage(file="Jump_pink.png"),
            'PhotoHero' : PhotoImage(file='Jump_pink_big.png'), 
            'HeroName' : 'PyjaMask',
            'MapName' : 'DreamLand'
        }

        self.texture_3 = {  # medieval texture
            'chemin': [PhotoImage(file="ground_0.png"),
                    PhotoImage(file="ground_0.png"),
                    PhotoImage(file="ground_1.png")],
            'background' : PhotoImage(file='back.png'),
            'sword' : PhotoImage(file='brick.png'),
            'Goblin': PhotoImage(file="goblin.png"),

            'Bat': PhotoImage(file="bat.png"),
            'Blob': PhotoImage(file="blob.png"),
            'Ork': PhotoImage(file="orc.png"),
            'Dragon': PhotoImage(file="dragon.png"),

            'potion': PhotoImage(file="potion_heal.png"),
            'telepotion' : PhotoImage(file='potion_teleport.png'),
            'portoloin': PhotoImage(file="portoloin.png"),
            'food': PhotoImage(file="beef_raw.png"),

            'bow': PhotoImage(file="bow.png"),
            'chainmail': PhotoImage(file="armor_iron.png"),

            'Hero': PhotoImage(file="Red_Knight.png"),
            'PhotoHero' : PhotoImage(file='Red_Knight_big.png'),
            'HeroName' : 'The Christophe',
            'MapName' : 'Corsican BattleField'
        }

        self.texture_4 = { # forest texture
            'chemin' : [PhotoImage(file='grass1.png'),
                        PhotoImage(file='grass2.png'),
                        PhotoImage(file='grass3.png')],
            'background' : PhotoImage(file='back4.png'),

            'Goblin': PhotoImage(file="wandering_mushroom.png"),
            'Bat': PhotoImage(file="small_snake.png"),
            'Blob': PhotoImage(file="plant.png"),
            'Ork': PhotoImage(file="troll.png"),
            'Dragon': PhotoImage(file="lindwurm.png"),

            'chainmail': PhotoImage(file="buckler1.png"),

            'Hero': PhotoImage(file="Frog.png"),
            'PhotoHero' : PhotoImage(file='Frog_big.png'),
            'HeroName' : 'FrogMan',
            'MapName' : 'Strange Forest'

        }



        self.chooseTexture()

        self.addWindow()  # on crée la fenetre

        self.window_h = 720  # self.fenetre.winfo_height()
        self.window_w = 1080  # self.fenetre.winfo_width()

        self.infoScreen()
        self.userText()
        self.infoText()
        self.infoActions()

        self.addGround()
        self.addMap()
        self.addObj()

        self.terrain.pack(anchor='w')

    def addWindow(self):
        """Creates the window of the interface"""
        self.fenetre.minsize(1080, 720)
        self.fenetre.maxsize(1080, 720)
        self.fenetre.geometry("1080x720")
        self.fenetre.iconbitmap("test.ico")
        self.fenetre.title("Mix of space and time")
        self.fenetre.config(bg='black')

    def addGround(self):
        """Adds the base for the map"""
        self.terrain = Canvas(master=self.fenetre, bg="black", height=self.window_h, width=self.window_h,
                             highlightthickness=0, name='terrain')  # frame qui va contenir tous les widg de la map
        self.terrain.create_image(self.window_h/2,self.window_h/2,
                                          image=self.texture['background'])           
        # self.terrain.place(x=self.window_h/2,y=self.window_w/2)
        self.terrain.pack(anchor='nw')

    def addMap(self):
        """Draws the map"""
        # self.fenetre.update()

        cote_canvas = self.window_h / 40
        o, p = 0, 0
        m, n = 0, 0  # sert pour le nom de la case
        for i in range(len(self.m._mat)):  # indice dans mat
            for j in self.m._mat[i]:  # element
                if j != self.m.empty:  # si l'element n'est pas un espace vide
                    case_i_j = Canvas(master=self.terrain, bg="white", height=cote_canvas, width=cote_canvas,
                                      highlightthickness=0, name=f'case_{n}_{m}')
                    case_i_j.create_image(cote_canvas / 2, cote_canvas / 2,
                                          image=(random.choice(self.texture['chemin'])))
                    case_i_j.place(x=o, y=p)

                m += 1
                o += cote_canvas
            o = 0
            n += 1
            p += cote_canvas

    def addObj(self):
        """Adds the objects"""
        o, p = 0, 0
        cote_canvas = self.window_h / 40

        for elem in self.m._elem:
            cd = self.m._elem[elem]  # on recupere les coords

            o, p = cd.x * cote_canvas, cd.y * cote_canvas

            obj_elem = Canvas(master=self.terrain,bg = "black", height=cote_canvas, width=cote_canvas,
                              highlightthickness=0, name=f'obj_{elem}_{cd}')
            obj_elem.create_image(cote_canvas / 2, cote_canvas / 2, image=(self.texture['chemin'])[0])   # image du fond 
            obj_elem.create_image(cote_canvas / 2, cote_canvas / 2, image=self.texture[f'{elem.name}'])
            obj_elem.place(x=o, y=p)

    def removeAllObj(self):
        """Deletes objects on the map"""
        for w in self.terrain.winfo_children():
            if str(w.winfo_name())[:3] == 'obj':
                w.destroy()

    def removeTerrain(self):
        """Deletes the ground"""
        for w in self.fenetre.winfo_children():
            if str(w.winfo_name())[:3] == 'terrain':
                w.destroy()

    def refreshGame(self):
        self.m = self.game.floor
        self.chooseTexture()

        self.removeTerrain()
        self.addGround()

        self.addMap()
        self.addObj()
        self.refreshText()

    def infoScreen(self):
        """Creates a frame to contain widgets for user's info """
        info_w = self.window_w - self.window_h
        self.infoSc = Frame(master=self.fenetre, bg='black', width=info_w, height=self.window_h)
        self.infoSc.place(x=self.window_h, y=0)

    def infoText(self):
        """Shows the informations about the hero"""

        heroLevel = self.game.hero.level
        self.heroLvl = Label(master=self.infoSc, text=f'Level : {heroLevel}', bg='black', name='lvl', fg = 'white',
                                font=('Helvetica',13, 'bold'))
        self.heroLvl.place(x=20, y=40)

        heroStr = self.game.hero.strength
        self.heroStr = Label(master=self.infoSc, text=f'Strength : {heroStr}', bg='black', name='stg', fg = 'white',
                                font=('Helvetica',13, 'bold'))
        self.heroStr.place(x=20, y=60)

        heroXp = self.game.hero.xp 
        self.heroXp = Label(master=self.infoSc, text=f'XP : {heroXp} / {heroLevel * 5}',bg='black', name='xpt', fg = 'white',
                                font=('Helvetica',13, 'bold'))
        self.heroXp.place(x=150, y=40)

        floor = self.game.gameLevel
        self.heroFloor = Label(master=self.infoSc, text=f'Floor : {floor}',bg='black', name='flr', fg = 'white',
                                font=('Helvetica',13, 'bold'))
        self.heroFloor.place(x=150, y=60)

        heroName = self.texture['HeroName']
        self.heroName = Label(master=self.infoSc, text=heroName ,bg='black', fg='white', name='hNm',
                                font=('Helvetica', 18, 'bold'))
        self.heroName.place(x=60, y=0)

        mapName = self.texture['MapName']
        self.mapName = Label(master=self.infoSc, text=f'World : {mapName}' ,bg='black', fg='white', name='mNm',
                                font=('Helvetica', 16, 'bold'))
        self.mapName.place(x=50,y=160)

        gold = str(len(self.game.hero._inventory[1]))
        self.gold = Label(master=self.infoSc, image=self.texture['gold'], text=f' : {gold}', compound='left',
                            fg='white', bg='black' ,name='gld',font=('Helvetica', 13, 'bold'))
        self.gold.place(x=20,y=100)
        

    def infoActions(self):
        """Shows the actions"""

        self.boxActions=Frame(master=self.infoSc, bg='black', width=360, height=140, bd=2, relief=SUNKEN)
        self.boxActions.place(x=0, y=500)

        self.labelActions = Label(master=self.boxActions,bg='black', text='Actions : ', fg='white')
        self.labelActions.place(x=0,y=0)

        actionInfo = self.game.readMessages()
        self.actionInfo = Label(master=self.boxActions, text=f'{actionInfo}', bg='black', wraplength=360, fg='white')
        self.actionInfo.place(x=0, y=20)

    def chooseTexture(self):
        """Choses a texture for the ground"""
        l = self.game.gameLevel
        if l % 4 == 0:
            for key in self.texture_1:
                self.texture[f'{key}'] = self.texture_1[f'{key}']

        elif l % 4 == 1:
            for key in self.texture_2:
                self.texture[f'{key}'] = self.texture_2[f'{key}']


        elif l % 4 == 2:
            for key in self.texture_3:
                self.texture[f'{key}'] = self.texture_3[f'{key}']

        else : 
            for key in self.texture_4:
                self.texture[f'{key}'] = self.texture_4[f'{key}']
            

    def userText(self):
        """Displays information for the user"""
        self.photoHero = Canvas(master=self.infoSc, bg='black', width=100, height=100, highlightthickness=0)
        self.photoHero.create_image(50,50,image=self.texture['PhotoHero'])
        self.photoHero.place(x=260, y=0)

        self.displayInvent()
        self.displayLife()
        self.displaySatiety()
        self.infoText()

    def displayInvent(self):
        """Displays the hero's inventory"""

        self.inventBox = Frame(master=self.infoSc, width=360, height=85,bg='black')
        self.inventBox.place(x=0, y=330)

        o , p = 1 , 20 
        invent = self.game.hero._inventory[0]
        for i in range(10):
            l =['&','é', '"', "'", '(', '-', 'è', '_','ç','à']

            self.num = Label(master=self.inventBox, text=f'{i}', bg='black', fg='white', name=f'num_{o}_{p}')
            self.num.place(x=o+14, y=0)

            self.let = Label(master=self.inventBox, text=f'{l[i]}', bg='black', fg='white', name=f'let_{o}_{p}')
            self.let.place(x=o+14, y=p+40)
            
            self.inventDis = Canvas(master=self.inventBox, width=30, height=30, bg='black', name=f'inv_{o}_{p}')
            if i < len(invent):
                item = 0
                self.inventDis.create_image(16,18,image=self.texture[f'{invent[i].name}'])
            self.inventDis.place(x=o,y=p)
            
            o+=35
    
    def displayLife(self):
        """Displays the heros' health points"""
        o , p = 13 , 270
        hp = self.game.hero.hp
        hpM = self.game.hero.hpMax 

        for i in range(hpM):
            self.heart = Canvas(master=self.infoSc, width=25, height=25, bg='black', highlightthickness=0,  name=f'life_{o}_{p}')
            if i < hp : 
                self.heart.create_image(13,12,image=self.texture['Full heart'])
            else:
                self.heart.create_image(13,12,image=self.texture['Empty heart'])
            self.heart.place(x=o, y=p)
            o+=30
            if i %10 == 0 and i!=0:
                p+=26
                o=13


    def displaySatiety(self):
        """Displays the heros' health points"""
        o , p = 13 , 240

        sat = self.game.hero.satiety
        satM = self.game.hero.satietyMax

        for i in range(0,satM, 5):
            self.heart = Canvas(master=self.infoSc, width=25, height=25, bg='black', highlightthickness=0,  name=f'sat_{o}_{p}')
            if i < sat : 
                self.heart.create_image(11,12,image=self.texture['Full food'])
            else:
                self.heart.create_image(11,12,image=self.texture['Empty food'])
            self.heart.place(x=o, y=p)
            o+=30
            if i %12 == 0 and i!=0:
                p+=25
                o=0

    def removeText(self):
        for w in self.terrain.winfo_children():
            if str(w.winfo_name())[:3] in ['lvl', 'stg', 'xpt', 'flr', 'hNm','mNm', 'gld' ]:
                w.destroy()

    
    def removeDisplays(self):
        for w in self.inventBox.winfo_children():
            if str(w.winfo_name())[:3] in ['let','num','inv','sat','life']:
                w.destroy()


    def refreshText(self):
        self.removeText()
        self.infoText()

        self.removeDisplays()
        self.userText()

    def refreshActions(self,newActions):
        self.actionInfo['text'] = newActions

    def gameOver(self):
        self.removeTerrain()
        self.removeAllObj()

        self.texture['background'] = PhotoImage(file='game_over_screen.png')
        self.addGround()





            
            



########################################################################################


def theGame(game=Game()):  # singleton qui permet de n'avoir qu'une instance de game()
    return game


def userInterface(g):
    interface = Interface(game=g)
    return interface


def listMap():
    """Creates a list of ten/hundred maps"""
    listMap = []

    for i in range(1,100):
        m = Map(size=40, hero=theGame().hero, merchant=theGame().merchant)
        if i%3 == 0:
            m.addMerchant()
        listMap.append(m)

    return listMap


def oneListMap(listMap=listMap()):  # singleton de listMap
    return listMap


def heal(creature):
    if isinstance(creature, Creature):  # si la creature est bien une instance de creature

        if isinstance(creature, Hero):
            if creature.hp + 3 > creature.hpMax:  # si le hero recoit plus de hp que permis, on lui rajoute la différence
                creature.hp = creature.hpMax
                return True

        creature.hp += 3
        return True


def teleport(creature, unique):
    """Teleports creature to random room, in random empty cell"""

    g = theGame().floor  # la map du jeu
    rdRoom = random.choice(g._rooms)  # random room
    rdCoord = rdRoom.randEmptyCoord(g)  # random coord

    actualCoords = g.pos(creature)

    g.rm(actualCoords)  # on supprime l'ancienne creature
    g.put(rdCoord, creature)  # on met creature a nouvelle coord

    return unique


def eatFood(creature):
    """Gives back the hero his satiety"""
    if creature.satiety + 10 < creature.satietyMax :
        creature.satiety += 10
    else: 
        creature.satiety = creature.satietyMax

    return True


def hunger(creature):
    """Affects the hero's health depending on the satiety"""
    if theGame().turn % 5 == 0 and creature.satiety > 0:
        creature.satiety -= 1

    if creature.satiety == 0:
        creature.hp -= 1

def exchange(d,m):
    """Exchanges two dictionnaries"""
    inter = d.copy() 
    d.clear()
    for key in m:
        d[f'{key}'] = m[f'{key}']

    m.clear()
    for key in inter:
        m[f'{key}'] = inter[f'{key}']

def Heroplay(self, interface):
    """Main game loop"""

    base_map = self.floor  # map de base
    base_textHero = self.hero.fullDescription()  # text de base
    base_textActions = self.readMessages() #actions de base

    while self.hero.hp > 0:
        
        interface.terrain.focus_set()
        interface.terrain.bind("<Key>", clavier)
        
        interface.removeAllObj()  # on supp tout

        if self.floor != base_map:
            base_map = self.floor  # le nouvel etage
            interface.refreshGame()  # on met a jour la map

        if interface.game.hero.fullDescription() != base_textHero:
            base_textHero = interface.game.hero.fullDescription()
            interface.refreshText()

        interface.addObj()  # on ajoute tous les éléments
        interface.fenetre.update()

        newMsg = self.readMessages()
        if newMsg!= base_textActions and newMsg != '' :#and interface.game.readMessages() != []:
            base_textActions = newMsg
            interface.refreshActions(base_textActions)
    
    interface.gameOver()
    interface.fenetre.mainloop()


def letsPlay(self):
    self.buildFloor()
    self.createFloors()

    interface = userInterface(self)  # création d'une interface liée a theGame
    interface.addMap()

    Heroplay(self, interface)

##################################################################################

g = theGame()

letsPlay(g)
