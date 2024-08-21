import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import statistics


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.defense_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.
        self.scoutv3(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def scoutv3(self, game_state):
        # attack first
        mp = game_state.get_resource(MP)
        extra = game_state.turn_number // 10
        distrib = self.defensive_balance(game_state)

        if game_state.get_resource(MP, 1) > 14:
            opp_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
            deploy_locations = self.filter_blocked_locations(opp_edges, game_state)
            loc = self.least_damage_spawn_location(game_state,deploy_locations ,1)
            game_state.attempt_spawn(INTERCEPTOR, loc)
        if mp >= 10 + extra:
            self.scout_least_damage_spam(game_state, support=True)
        if game_state.my_health < 15:
            self.build_front_reactive(game_state)
            self.build_defences(game_state)
        else:
            self.build_defences(game_state)
            self.build_front_reactive(game_state)

    def distrib_defense(self, game_state, distrib):
        #LeftLeft (2-7) LeftMid (8-13) RightMid (14-19) RightRight (20-25) 
        LL_turrets = [[4, 12], [3, 12], [5, 12], [2, 12], [6,12], [1,12], [7,12]]
        LL_walls = [[loc[0],loc[1]+1] for loc in LL_turrets]
        RR_turrets = [[23, 12], [24, 12], [22, 12], [25, 12], [21,12], [26,12], [20,12]]
        RR_walls = [[loc[0],loc[1]+1] for loc in RR_turrets]
        LM_turrets = [[10, 12], [9, 12], [11, 12], [8, 12], [12,12], [13,12]]
        LM_walls = [[loc[0],loc[1]+1] for loc in LM_turrets]
        RM_turrets = [[17, 12], [18, 12], [16, 12], [19, 12], [15,12], [14,12]]
        RM_walls = [[loc[0],loc[1]+1] for loc in RM_turrets]

        sp = game_state.get_resource(SP)
        alloc = [sp*i for i in distrib] # point allocation
        for i in range(len(alloc)):
            pass



    def defensive_balance(self, game_state):
        '''
        Calculate rating of defense for each section of defenses, based on health, damage, urgency

        Equation: ((SUM_turrets(health) + 1.5*SUM_wall(health))  * damage) ^ urgency
        
        Higher rating = stronger
        Distrib should come out to a probability vector
        '''
        # add urgency if recently attacked
        distrib = [0,0,0,0] #LeftLeft (2-7) LeftMid (8-13) RightMid (14-19) RightRight (20-25) 
        health, damage = [0,0,0,0], [0,0,0,0]
        urgency = self.get_urgency(game_state)
        for i in range(2,26):
            ind = (i-2) // 6
            turret = game_state.contains_stationary_unit([i,12])
            wall = game_state.contains_stationary_unit([i,13])
            if turret:
                damage[ind] += turret.damage_i * turret.attackRange
                health[ind] += turret.health
            if wall:
                health[ind] += 1.5 * wall.health
        #softmax like calculation
        for i in range(len(distrib)):
            distrib[i] = (health[i] * damage[i]) ** (1/urgency[i])
        avg = sum(distrib)/4
        for i in range(len(distrib)):
            distrib[i] /= avg
            distrib[i] = math.exp(distrib[i])
        maxx = max(distrib)
        for i in range(len(distrib)):
            distrib[i] = abs(distrib[i]-maxx)
        sumx = sum(distrib)
        for i in range(len(distrib)):
            distrib[i] /= sumx
        
        return distrib

    def get_urgency(self, game_state):
        '''
        Equation = SUM_goals((how recently scored) * relevancy) --> normalized so highest urgency is 1
        '''
        urg = [10,10,10,10]
        sc = self.scored_on_locations
        for i in range(len(sc)):
            if sc[i][0] <= 3:
                urg[0] += (i/len(sc))
            elif sc[i][0] <= 5:
                urg[0] += (i/len(sc)) * .5
                urg[1] += (i/len(sc)) * .5
            elif sc[i][0] <= 9:
                urg[1] += (i/len(sc)) * .5
                urg[2] += (i/len(sc)) * .5
            elif sc[i][0] <= 13:
                urg[2] += (i/len(sc)) * .5
                urg[3] += (i/len(sc)) * .5
            elif sc[i][0] <= 18:
                urg[0] += (i/len(sc)) * .5
                urg[1] += (i/len(sc)) * .5
            elif sc[i][0] <= 22:
                urg[1] += (i/len(sc)) * .5
                urg[2] += (i/len(sc)) * .5
            elif sc[i][0] <= 27:
                urg[3] += (i/len(sc)) 
        maxx = max(urg)
        for i in range(len(urg)):
            urg[i] /= maxx
        return urg

    def scout_least_damage_spam(self, game_state, count=1000, support=False):
        '''
        Finds that best path for scouts currently, and then have the option to temporarily spawn a 
        support nearby for the round
        '''
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)

        suboptimal_shields = [[0, 13], [1, 13], [2, 13], [3, 13], [4, 13], [5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13], [11, 13], [12, 13], [13, 13], [14, 13], [15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13], [23, 13], [24, 13], [25, 13], [26, 13], [27, 13], [2, 11], [3, 11], [24, 11], [25, 11], [3, 10], [4, 10], [23, 10], [24, 10], [4, 9], [5, 9], [22, 9], [23, 9], [5, 8], [6, 8], [21, 8], [22, 8], [6, 7], [7, 7], [20, 7], [21, 7], [7, 6], [8, 6], [19, 6], [20, 6], [8, 5], [9, 5], [18, 5], [19, 5], [9, 4], [10, 4], [17, 4], [18, 4], [10, 3], [11, 3], [16, 3], [17, 3], [11, 2], [12, 2], [15, 2], [16, 2], [12, 1], [13, 1], [14, 1], [15, 1], [13, 0], [14, 0]]
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        safest, damage = self.least_damage_spawn_location_v2(game_state, deploy_locations, 0, True)
        game_state.attempt_spawn(SCOUT, safest, count)
        if support:
            supp_loc = [safest[0], safest[1]+2]
            taken = game_state.contains_stationary_unit(supp_loc) and game_state.contains_stationary_unit(supp_loc) != SUPPORT 
            while taken:
                if safest[0] <= 13:
                    supp_loc[0] += 1
                else:
                    supp_loc[0] -= 1 
                taken = game_state.contains_stationary_unit(supp_loc) and game_state.contains_stationary_unit(supp_loc) != SUPPORT
            #flag = 
            #if flag:
            #    game_state.attempt_upgrade(SUPPORT, supp_loc)
            #game_state.attempt_upgrade(supp_loc)
            game_state.attempt_spawn(SUPPORT, supp_loc)
            game_state.attempt_remove(supp_loc)

        return safest, damage

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[4, 12],[23, 12], [10, 12], [17, 12], [3, 12], [24,12]]
         
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)
        
        # Place walls in front of turrets to soak up damage for them
        wall_locations = [[10, 13], [23, 13], [17, 13], [4, 13]]
        edge_wall =[[0, 13], [1, 13], [2, 13], [3, 13], [4, 13], [25, 13], [26, 13], [27, 13]]
        game_state.attempt_spawn(WALL, wall_locations)
        game_state.attempt_upgrade(turret_locations)
        game_state.attempt_upgrade(wall_locations)
        # upgrade walls so they soak more damage

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        defense = self.scored_on_locations
        opponent_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
        opp = self.filter_blocked_locations(opponent_edges, game_state)
        vulnerable = self.least_damage_spawn_location_v2(game_state,opp,1)
        if vulnerable[0] <= 13:
            defense =  [vulnerable] + self.scored_on_locations 
        else:
            defense = [vulnerable] + self.scored_on_locations
        for location in defense:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            diff = 1
            if location[0] > 13:
                diff = -1
            turret_location = [[location[0], location[1]+1],[location[0]+diff, location[1]+1]]
            game_state.attempt_upgrade(turret_location)
            game_state.attempt_spawn(TURRET, turret_location)

    def build_front_reactive(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from/most vulnerable
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function. 
        this functions builds only on the front line
        """
        turret_front = [[3, 12], [24, 12], [9, 12], [18, 12]] # 0 = LL, 1=RR, 2=LM, 3= RM.... LeftRightMiddle
        wall_front_edge = [[0, 13], [1, 13], [2, 13], [8, 13], [11, 13], [16, 13], [19, 13],[25, 13], [26, 13], [27, 13]]
        
        turret_locations = turret_front
        if len(self.scored_on_locations) >= 1:
            turret_locations = self.predictive_turret_locations(self.scored_on_locations[::1]) + turret_front
            last_scored = self.scored_on_locations[-1]
        
        wall_turrets = [[location[0], location[1]+1] for location in turret_locations],[[location[0]+1, location[1]+1] for location in turret_locations], [[location[0]-1, location[1]+1] for location in turret_locations]
        for j in range(len(wall_turrets)):
            for i in range(len(turret_locations)):
                game_state.attempt_spawn(TURRET, turret_locations[i])
                game_state.attempt_upgrade(turret_locations[i])
                game_state.attempt_spawn(WALL, wall_turrets[j][i])
                game_state.attempt_upgrade(wall_turrets[j][i])

        if game_state.get_resource(SP) > 20:
            game_state.attempt_spawn(WALL, wall_front_edge)
            game_state.attempt_upgrade(wall_front_edge)

    def predictive_turret_locations(self, locations:list[list[int]]):
        locs = []
        for loc in locations:
            x, y = loc
            if loc[0] <= 13:
                x += (13-y)
            else:
                x -= (13-y)
            locs.append([x, 12])
            locs.append([x+1, 12])
            locs.append([x-1, 12])

        return locs

    def least_damage_spawn_location_v2(self, game_state, location_options, user=0, want_damage=False):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        Choose the user, 0 for yourself, 1 for opponent. 1 will return your most vulnerable spawn point
        equivalently the most vulnerable goal for your opp.
        """
        damages = []
        # Get the damage estimate each path will take
        vulnerable = []
        if len(location_options) == 0:
            return
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            if len(path) < 20:
                damages.append(float('infinity'))
                continue
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                for attacker in game_state.get_attackers(path_location, user):
                    # reduce damage by a factor of health + surrounding walls to encourage taking paths where we'll likely destroy turrets
                    damage += gamelib.GameUnit(TURRET, game_state.config).damage_i * min(200, max(25, attacker.health + 0.2*self.get_surrounding_wall_health(game_state, attacker)))
            damages.append(damage)
            if user == 1:
                vulnerable.append(path[-1])

        # Now just return the location that takes the least damage
        if want_damage:
            return ((location_options[damages.index(min(damages))],min(damages)) if user == 0 else (vulnerable[damages.index(min(damages))], min(damages)))

        return (location_options[damages.index(min(damages))] if user == 0 else vulnerable[damages.index(min(damages))])
    
    def get_surrounding_wall_health(self, game_state, attacker):
        #obtain all points within the bottom half of the area the turret covers
        health = 0

        radial_locations = game_state.game_map.get_locations_in_range([attacker.x, attacker.y], 4)
        filtered_points = [point for point in radial_locations if point[1] <= attacker.y]
        
        for point in filtered_points:
            wall = game_state.contains_stationary_unit(point)
            if wall == WALL:
                health += wall.health
        
        return health

    def least_damage_spawn_location(self, game_state, location_options, user=0, want_damage=False):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        Choose the user, 0 for yourself, 1 for opponent. 1 will return your most vulnerable spawn point
        equivalently the most vulnerable goal for your opp.
        """
        damages = []
        # Get the damage estimate each path will take
        vulnerable = []
        if len(location_options) == 0:
            return
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            if len(path) < 20:
                damages.append(float('infinity'))
                continue
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, user)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
            if user == 1:
                vulnerable.append(path[-1])
        # Now just return the location that takes the least damage
        if want_damage:
            return ((location_options[damages.index(min(damages))],min(damages)) if user == 0 else (vulnerable[damages.index(min(damages))], min(damages)))

        return (location_options[damages.index(min(damages))] if user == 0 else vulnerable[damages.index(min(damages))])

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
