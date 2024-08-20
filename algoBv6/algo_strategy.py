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
        self.scoutv2(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def scoutv2(self, game_state):
        # attack first
        mp = game_state.get_resource(MP)
        # if game_state.my_health < 15:
        #     self.interceptor_predict(game_state)
        if mp >= 10:
            loc, damage = self.scout_least_damage_spam(game_state, count=int(mp-3), support=True)
            if damage < 20:
                if loc[0] <= 13:
                    game_state.attempt_spawn(DEMOLISHER, [loc[0]-1,loc[1]+1])
                else:
                    game_state.attempt_spawn(DEMOLISHER, [loc[0]+1,loc[1]+1])
            else:
                game_state.attempt_spawn(SCOUT, loc, 3)
        self.build_defences(game_state)
        self.build_front_reactive(game_state)

    def scout_least_damage_spam(self, game_state, count=1000, support=False):
        '''
        Finds that best path for scouts currently, and then have the option to temporarily spawn a 
        support nearby for the round
        '''
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)

        suboptimal_shields = [[0, 13], [1, 13], [2, 13], [3, 13], [4, 13], [5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13], [11, 13], [12, 13], [13, 13], [14, 13], [15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13], [23, 13], [24, 13], [25, 13], [26, 13], [27, 13], [1, 12], [2, 12], [3, 12], [4, 12], [5, 12], [6, 12], [7, 12], [8, 12], [9, 12], [10, 12], [11, 12], [12, 12], [13, 12], [14, 12], [15, 12], [16, 12], [17, 12], [18, 12], [19, 12], [20, 12], [21, 12], [22, 12], [23, 12], [24, 12], [25, 12], [26, 12], [2, 11], [3, 11], [24, 11], [25, 11], [3, 10], [4, 10], [23, 10], [24, 10], [4, 9], [5, 9], [22, 9], [23, 9], [5, 8], [6, 8], [21, 8], [22, 8], [6, 7], [7, 7], [20, 7], [21, 7], [7, 6], [8, 6], [19, 6], [20, 6], [8, 5], [9, 5], [18, 5], [19, 5], [9, 4], [10, 4], [17, 4], [18, 4], [10, 3], [11, 3], [16, 3], [17, 3], [11, 2], [12, 2], [15, 2], [16, 2], [12, 1], [13, 1], [14, 1], [15, 1], [13, 0], [14, 0]]
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        safest, damage = self.least_damage_spawn_location(game_state, deploy_locations, 0, True)
        game_state.attempt_spawn(SCOUT, safest, count)
        if support:
            supp_loc = [[safest[0], safest[1]+2], [safest[0], safest[1]+3]]
            taken = game_state.contains_stationary_unit(supp_loc[0]) and game_state.contains_stationary_unit(supp_loc[1])
            while taken:
                if safest[0] <= 13:
                    supp_loc[0][0] += 1
                    supp_loc[1][0] += 2
                else:
                    supp_loc[0][0] -= 1 
                    supp_loc[1][0] -= 2
                taken = game_state.contains_stationary_unit(supp_loc[0]) and game_state.contains_stationary_unit(supp_loc[1])
            #supp_loc = [loc for loc in supp_loc if loc not in suboptimal_shields]
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
        # upgrade walls so they soak more damage
        game_state.attempt_upgrade(turret_locations)
        game_state.attempt_upgrade(wall_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        defense = self.scored_on_locations
        opponent_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
        opp = self.filter_blocked_locations(opponent_edges, game_state)
        vulnerable = self.least_damage_spawn_location(game_state,opp,1)
        if vulnerable[0] <= 13:
            defense =  [vulnerable] + self.scored_on_locations 
        else:
            defense = [vulnerable] + self.scored_on_locations
        for location in defense:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            diff = 1
            if location[0] > 13:
                diff = -1
            turret_location = [[location[0], location[1]+1,],[location[0]+diff, location[1]+1]]
            game_state.attempt_spawn(TURRET, turret_location)
            #game_state.attempt_upgrade(turret_location)

    def build_front_reactive(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from/most vulnerable
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function. 
        this functions builds only on the front line
        """
        turret_front = [[3, 12], [24, 12], [9, 12], [18, 12]]
        wall_front = [[location[0], location[1]+1] for location in turret_front] + [[location[0]+1, location[1]+1] for location in turret_front] + [[location[0]-1, location[1]+1] for location in turret_front]
        wall_front_edge = [[0, 13], [1, 13], [2, 13], [8, 13], [11, 13], [16, 13], [19, 13],[25, 13], [26, 13], [27, 13]]
        
        turret_locations = turret_front + self.predictive_turret_locations()

        game_state.attempt_spawn(TURRET, turret_front + turret_locations)
        game_state.attempt_upgrade(turret_locations)
        game_state.attempt_spawn(WALL, wall_front)
        game_state.attempt_upgrade(wall_front)
        if len(self.scored_on_locations) > 10 and (game_state.get_resource(SP) > 20):
            game_state.attempt_spawn(WALL, wall_front_edge)

    def predictive_turret_locations(self):
        locations: list[list[int]] = []
        
        for loc in self.scored_on_locations:
            locations.append([2*loc[0], 12])
            locations.append([2*loc[0]+1, 12])
            locations.append([2*loc[0]-1, 12])

        return locations

    def interceptor_predict(self,game_state):
        opp_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(opp_edges, game_state) 
        loc = self.least_damage_spawn_location(game_state, deploy_locations, 1) 
        # loc is the most vulnerable to attack spot
        game_state.attempt_spawn(INTERCEPTOR, loc)


    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

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
