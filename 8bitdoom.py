from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
import math
import random


# --- Constants and Global Game Variables ---
# Window
SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 768
# Game States
STATE_PLAYING = 0
STATE_LEVEL_TRANSITION = 1
STATE_GAME_OVER_TRANSITION = 2
STATE_YOU_WIN = 3
# UI/Menu States
STATE_MAIN_MENU = 100
STATE_LEVEL_SELECT = 101
STATE_HALL_OF_FAME = 102
STATE_PAUSED = 103

game_state = STATE_MAIN_MENU
current_level = 1
max_levels = 10

# Player settings
PLAYER_SPEED = 5.0
PLAYER_ROTATE_ANGLE = 0.5
PLAYER_TOTAL_HEIGHT = 1.8
PLAYER_BODY_Y_OFFSET = PLAYER_TOTAL_HEIGHT / 2 
PLAYER_EYE_HEIGHT_FROM_MODEL_BASE = 1.6 
PLAYER_RADIUS = 0.5 
PLAYER_MAX_HEALTH = 100
PLAYER_BASE_SHOOT_COOLDOWN_TIME = 0.3

# Player model proportions
PLAYER_LEG_LENGTH = PLAYER_TOTAL_HEIGHT * 0.45
PLAYER_TORSO_HEIGHT = PLAYER_TOTAL_HEIGHT * 0.4
PLAYER_ARM_LENGTH = PLAYER_TOTAL_HEIGHT * 0.35
PLAYER_GUN_LENGTH = PLAYER_TOTAL_HEIGHT * 0.3

# Bullet settings
BULLET_SPEED = 30.0
BULLET_RADIUS = 0.1
BULLET_LIFESPAN = 2.5

# Enemy settings
ENEMY_MIN_DISTANCE_FROM_PLAYER = 3.5
ENEMY_BASE_COLLISION_RADIUS = 0.6

# Perk System Variables
PERK_SCORE_MULTIPLIER_DURATION = 5.0
PERK_RAPID_FIRE_DURATION = 5.0

# Dungeon settings
DUNGEON_SIZE_X = 100.0
DUNGEON_SIZE_Z = 100.0
WALL_HEIGHT = 8.0
TILE_SIZE = 5.0

# Camera
CAMERA_MODE_FIRST_PERSON = 0
CAMERA_MODE_THIRD_PERSON = 1
camera_mode = CAMERA_MODE_THIRD_PERSON
tp_camera_distance = 8.0
tp_camera_pitch = -30.0
tp_camera_yaw_offset = 0.0

# Global lists for game objects
player = {}
enemies = []
bullets = []

# Level Management
level_configs = {}
enemies_killed_this_level = 0
enemies_spawned_this_level = 0
boss_entity = None

# Cheat mode (auto-fire + godmode)
cheat_mode = False
cheat_fire_timer = 0.0
CHEAT_SHOOT_INTERVAL = 0.18  # seconds between auto shots

# Smooth facing
PLAYER_TURN_SPEED_DEG_PER_SEC = 240.0

# Score record guard
win_score_recorded = False
current_session_score_recorded = False

# Level obstacles (pillars/blocks) for simple level design improvements
obstacles = []  # each: {'pos':[x,z], 'radius': r, 'height': h, 'color':[r,g,b], 'shape': 'cyl'|'box'}

# Enemy animation timer
enemy_anim_time = 0.0

# Timing
last_time = 0.0
transition_timer = 0.0
TRANSITION_DURATION = 1.5
transition_color = [0.0, 0.0, 0.0]
next_game_state_after_transition = STATE_PLAYING

# Input states
keys_pressed = {}
special_keys_pressed = {}
mouse_buttons = {}
mouse_pos = {'x': 0, 'y': 0}

# UI Palette - Dark dungeon/action game theme
UI_COLORS = {
    'bg_main_top': (0.02, 0.02, 0.05),
    'bg_main_bottom': (0.01, 0.01, 0.03),
    'panel': (0.08, 0.08, 0.12),
    'panel_shadow': (0.0, 0.0, 0.0, 0.7),
    'btn_primary': (0.15, 0.35, 0.85),  # Blue accent
    'btn_secondary': (0.15, 0.65, 0.35),  # Green accent
    'btn_warn': (0.75, 0.15, 0.15),  # Red accent
    'btn_neutral': (0.20, 0.20, 0.25),
    'title': (0.95, 0.95, 1.0),
    'subtitle': (0.80, 0.85, 0.90),
    'accent_gold': (0.95, 0.75, 0.25),
    'accent_red': (0.90, 0.20, 0.20)
}

# UI buttons storage for hit-testing in current frame: list of dicts {label, x, y, w, h, action}
ui_buttons = []

# High scores (in-memory per run) - keep only recent top 3
hof_records = []  # list of {'score': int, 'seq': int}
hof_seq = 0

# GLU Quadric object for cylinders
glu_quadric = None

# --- Helper Functions (Math, etc.) ---
def vector_length(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def normalize_vector(v):
    l = vector_length(v)
    if l == 0:
        return [0,0,0]
    return [v[0]/l, v[1]/l, v[2]/l]

def distance_3d(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)

def check_sphere_collision(pos1, radius1, pos2, radius2):
    dist = distance_3d(pos1, pos2)
    return dist < (radius1 + radius2)

# --- Game Object Initialization and Management ---
def init_player():
    """Initialize the player dictionary with position, rotation, health, score,
    perk counters/timers and the current shooting cooldown baseline."""
    global player
    player = {
        'pos': [DUNGEON_SIZE_X / 2, PLAYER_BODY_Y_OFFSET, DUNGEON_SIZE_Z / 2], 
        'rotation_y': 0.0, 'rotation_x': 0.0,
        'health': PLAYER_MAX_HEALTH, 'score': 0, 'speed': PLAYER_SPEED,
        'shoot_cooldown': 0.0, 'current_shoot_cooldown_time': PLAYER_BASE_SHOOT_COOLDOWN_TIME,
        'kills_for_health_perk': 0, 'kills_for_score_perk': 0, 'kills_for_gun_perk': 0,
        'health_perk_available': False, 'score_perk_available': False, 'gun_perk_available': False,
        'score_perk_time_left': 0.0, 'gun_perk_time_left': 0.0,
    }

def get_enemy_definition(enemy_type_id):
    """Return an enemy configuration dict for a given type id.
    Includes health, damage, speed multiplier, model height, color (by theme), and points."""
    # Define colors based on current level theme
    if current_level <= 3:
        # Earth theme (lush greens)
        type1_color = [0.20, 0.85, 0.30]
        type2_color = [0.10, 0.70, 0.25]
        type3_color = [0.06, 0.55, 0.18]
    elif current_level <= 6:
        # Mud theme (rich browns)
        type1_color = [0.75, 0.55, 0.30]
        type2_color = [0.60, 0.40, 0.20]
        type3_color = [0.45, 0.30, 0.15]
    elif current_level <= 9:
        # Heaven theme (light blue/white tints)
        type1_color = [0.85, 0.95, 1.00]
        type2_color = [0.70, 0.85, 1.00]
        type3_color = [0.60, 0.80, 0.98]
    else:
        # Hell theme (crimson/ember reds)
        type1_color = [0.90, 0.20, 0.15]
        type2_color = [0.80, 0.12, 0.10]
        type3_color = [0.70, 0.08, 0.06]

    if enemy_type_id == 1:
        return {
            'name': 'Type1Wolf',
            'health': 3,  # Takes 3 hits to kill
            'damage': 5,  # Deals 5hp damage
            'speed_mult': 0.2,
            'model_height': 2.0,
            'color': type1_color,
            'points': 10
        }
    elif enemy_type_id == 2:
        return {
            'name': 'Type2Wolf',
            'health': 4,  # Takes 4 hits to kill
            'damage': 6,  # Reduced from 8 to 6
            'speed_mult': 0.3,  # Reduced from 0.4 to 0.3
            'model_height': 3.0,
            'color': type2_color,
            'points': 15
        }
    elif enemy_type_id == 3:
        return {
            'name': 'Type3Wolf',
            'health': 5,  # Takes 5 hits to kill
            'damage': 8,  # Reduced from 11 to 8
            'speed_mult': 0.4,  # Reduced from 0.6 to 0.4
            'model_height': 4.0,
            'color': type3_color,
            'points': 20
        }
    elif enemy_type_id == 'miniboss':
        return {
            'name': 'MiniBossWolf',
            'health': 10, # Takes 10 hits to kill
            'damage': 10, # Reduced from 13 to 10
            'speed_mult': 0.5,  # Reduced from 0.8 to 0.5
            'model_height': 6.0,
            'color': [0.95, 0.15, 0.15],  # Bright red color for miniboss
            'points': 50,
            'is_boss': True
        }
    elif enemy_type_id == 'boss':
        return {
            'name': 'BossWolf',
            'health': 15, # Takes 15 hits to kill
            'damage': 12, # Reduced from 15 to 12
            'speed_mult': 0.6,  # Reduced from 1.0 to 0.6
            'model_height': 8.0,
            'color': [1.00, 0.08, 0.05],  # Deep red color for final boss
            'points': 100,
            'is_boss': True
        }
    return {}

def init_level_configs():
    """Create per-level enemy quotas and pools, and precompute spawn pools."""
    global level_configs
    level_configs = {
        1: {'total_enemies':5,'max_concurrent':1,'enemy_types':[1]}, 
        2: {'total_enemies':6,'max_concurrent':2,'enemy_types':[1]},
        3: {'total_enemies':9,'max_concurrent':3,'enemy_types':[1]}, 
        4: {'total_enemies':5,'max_concurrent':1,'enemy_types':[2]},
        5: {'total_enemies':7,'max_concurrent':1,'enemy_types':[1]*3+[2]*3+['miniboss'],'is_boss_level':True},
        6: {'total_enemies':9,'max_concurrent':3,'enemy_types':[2]},
        7: {'total_enemies':5,'max_concurrent':1,'enemy_types':[3]}, 
        8: {'total_enemies':6,'max_concurrent':2,'enemy_types':[3]},
        9: {'total_enemies':9,'max_concurrent':3,'enemy_types':[3]},
        10: {'total_enemies':16,'max_concurrent':1,'enemy_types':[1]*5+[2]*5+[3]*5+['boss'],'is_boss_level':True}
    }
    for i in range(1, max_levels + 1):
        level_configs[i]['enemies_to_spawn_pool'] = list(level_configs[i]['enemy_types'])

def spawn_enemy():
    """Spawn one enemy if allowed by the current level quotas and spacing rules."""
    global enemies_spawned_this_level, boss_entity, enemies
    level_conf = level_configs[current_level]
    if enemies_spawned_this_level >= level_conf['total_enemies']: 
        return
    enemy_type_to_spawn = None
    is_spawning_boss = False
    if 'is_boss_level' in level_conf:
        if not boss_entity and 'boss' in level_conf['enemies_to_spawn_pool']:
            enemy_type_to_spawn = 'boss'
            level_conf['enemies_to_spawn_pool'].remove('boss')
            is_spawning_boss = True
        elif level_conf['enemies_to_spawn_pool']:
            pool = [t for t in level_conf['enemies_to_spawn_pool'] if t != 'boss']
            if pool: 
                enemy_type_to_spawn = random.choice(pool)
                level_conf['enemies_to_spawn_pool'].remove(enemy_type_to_spawn)
    else:
        if level_conf['enemies_to_spawn_pool']: 
            enemy_type_to_spawn = level_conf['enemy_types'][0] 
    if enemy_type_to_spawn is None: 
        return
    config = get_enemy_definition(enemy_type_to_spawn)
    if not config: 
        return
    margin=7.0
    x=random.uniform(margin,DUNGEON_SIZE_X-margin)
    enemy_base_y=config['model_height']/2
    z=random.uniform(margin,DUNGEON_SIZE_Z-margin)
    min_spawn_dist_player=15.0
    min_spawn_dist_enemy=5.0
    spawn_attempts=0
    valid_spawn=False
    while spawn_attempts < 20 and not valid_spawn:
        valid_spawn=True
        if distance_3d([x,enemy_base_y,z],[player['pos'][0],player['pos'][1],player['pos'][2]]) < min_spawn_dist_player:
            valid_spawn=False
        for ex_en in enemies:
            if distance_3d([x,enemy_base_y,z],[ex_en['pos'][0],ex_en['pos'][1],ex_en['pos'][2]]) < min_spawn_dist_enemy:
                valid_spawn=False
                break
        if not valid_spawn: 
            x=random.uniform(margin,DUNGEON_SIZE_X-margin)
            z=random.uniform(margin,DUNGEON_SIZE_Z-margin)
        spawn_attempts+=1
    if not valid_spawn:
        if is_spawning_boss: 
            level_conf['enemies_to_spawn_pool'].insert(0,'boss')
        elif enemy_type_to_spawn and enemy_type_to_spawn != 'boss' and 'is_boss_level' in level_conf:
            level_conf['enemies_to_spawn_pool'].append(enemy_type_to_spawn)
        return
    new_enemy = {
        'pos':[x,enemy_base_y,z],'enemy_type_id':enemy_type_to_spawn,
        'max_health':config['health'],'health':config['health'],'damage':config['damage'],'speed':PLAYER_SPEED*config['speed_mult'],
        'reload_time':1.5/(config['speed_mult']+0.5),'shoot_cooldown':random.uniform(1.0,3.0),'points':config['points'],
        'color':config['color'],'model_height':config['model_height'],
        'collision_radius':ENEMY_BASE_COLLISION_RADIUS*(config['model_height']/1.8),
        'is_boss':config.get('is_boss',False),'rotation_y':0.0
    }
    enemies.append(new_enemy)
    enemies_spawned_this_level+=1
    if is_spawning_boss:
        boss_entity = new_enemy

def init_level(level_num):
    """Reset and prepare a level: clear entities, reset flags, place obstacles, and
    move the player to spawn."""
    global current_level,enemies,bullets,game_state,enemies_killed_this_level,enemies_spawned_this_level,boss_entity,player,win_score_recorded,obstacles,enemy_anim_time,current_session_score_recorded
    current_level=level_num
    enemies.clear()
    bullets.clear()
    boss_entity=None
    game_state=STATE_PLAYING
    enemies_killed_this_level=0
    enemies_spawned_this_level=0
    player['pos']=[DUNGEON_SIZE_X/2,PLAYER_BODY_Y_OFFSET,DUNGEON_SIZE_Z/2]
    player['rotation_y']=0.0
    player['rotation_x']=0.0
    player['health_perk_available']=False
    player['score_perk_available']=False
    player['gun_perk_available']=False
    player['score_perk_time_left']=0.0
    player['gun_perk_time_left']=0.0
    player['kills_for_health_perk']=0
    player['kills_for_score_perk']=0
    player['kills_for_gun_perk']=0
    level_configs[current_level]['enemies_to_spawn_pool'] = list(level_configs[current_level]['enemy_types'])
    win_score_recorded = False
    current_session_score_recorded = False
    enemy_anim_time = 0.0
    # Generate obstacles: vary by level theme
    obstacles = []
    random.seed(1000 + current_level)
    base_count = 8 + current_level // 2
    for i in range(base_count):
        rx = random.uniform(8.0, DUNGEON_SIZE_X-8.0)
        rz = random.uniform(8.0, DUNGEON_SIZE_Z-8.0)
        # Keep clear around player spawn center
        if distance_3d([rx,0,rz],[DUNGEON_SIZE_X/2,0,DUNGEON_SIZE_Z/2]) < 10.0:
            continue
        r = random.uniform(1.2, 2.2)
        h = random.uniform(3.0, 6.0)
        shape = 'cyl' if i % 2 == 0 else 'box'
        # Color by biome
        if current_level <= 3:
            col = [0.12, 0.35, 0.18]
        elif current_level <= 6:
            col = [0.45, 0.32, 0.18]
        elif current_level <= 9:
            col = [0.12, 0.22, 0.42]
        else:
            col = [0.45, 0.08, 0.45]
        obstacles.append({'pos':[rx,rz],'radius':r,'height':h,'color':col,'shape':shape})

def create_bullet(start_pos,direction_vec,owner_type,damage_val,color_override=None):
    """Append a bullet to the world with start position, direction, owner and damage."""
    bullets.append({'pos':list(start_pos),'dir':direction_vec,'owner':owner_type,'damage':damage_val,'lifespan':BULLET_LIFESPAN,
                    'color':color_override if color_override else ([1.0,1.0,0.0] if owner_type=='PLAYER' else [1.0,0.5,0.0])})

# --- Update Functions ---
def update_player(delta_time):
    """Advance player timers, process movement/rotation input, collisions and
    manage short-lived facing alignment assistance after firing."""
    global player,camera_mode,tp_camera_pitch,tp_camera_yaw_offset,align_to_camera_timer
    # Perk timers
    if player['score_perk_time_left']>0:
        player['score_perk_time_left']=max(0.0, player['score_perk_time_left']-delta_time)
        if player['score_perk_time_left']==0:
            pass  # Score Perk expired
    if player['gun_perk_time_left']>0:
        player['gun_perk_time_left']=max(0.0, player['gun_perk_time_left']-delta_time)
        if player['gun_perk_time_left']>0:
            player['current_shoot_cooldown_time']=0.001
        else:
            player['current_shoot_cooldown_time']=PLAYER_BASE_SHOOT_COOLDOWN_TIME
            pass  # Gun Perk expired
    else: 
        player['current_shoot_cooldown_time']=PLAYER_BASE_SHOOT_COOLDOWN_TIME
    
    speed = player['speed'] * delta_time
    dx, dz = 0, 0
    # WASD relative to view: third-person uses camera yaw; first-person uses player yaw
    if camera_mode == CAMERA_MODE_THIRD_PERSON:
        basis_yaw = tp_camera_yaw_offset
        # Camera forward on XZ is from camera to player: (-sin(yaw), cos(yaw))
        forward_x = -math.sin(math.radians(basis_yaw))
        forward_z =  math.cos(math.radians(basis_yaw))
        # Right is perpendicular clockwise: (cos(yaw), sin(yaw))
        right_x =  math.cos(math.radians(basis_yaw))
        right_z =  math.sin(math.radians(basis_yaw))
    else:
        basis_yaw = player['rotation_y']
        # Player forward on XZ should match look horizontal: (sin(yaw), cos(yaw))
        forward_x =  math.sin(math.radians(basis_yaw))
        forward_z =  math.cos(math.radians(basis_yaw))
        # Right is perpendicular clockwise: (cos(yaw), -sin(yaw))
        right_x =  math.cos(math.radians(basis_yaw))
        right_z = -math.sin(math.radians(basis_yaw))

    moved = False
    if keys_pressed.get(b'w'):
        dx += forward_x * speed; dz += forward_z * speed; moved = True
    if keys_pressed.get(b's'):
        dx -= forward_x * speed; dz -= forward_z * speed; moved = True
    if keys_pressed.get(b'a'):
        dx += right_x * speed; dz += right_z * speed; moved = True
    if keys_pressed.get(b'd'):
        dx -= right_x * speed; dz -= right_z * speed; moved = True
        
    WALL_MARGIN = PLAYER_RADIUS + 0.5
    new_x = player['pos'][0] + dx
    new_z = player['pos'][2] + dz
    
    if (WALL_MARGIN <= new_x <= DUNGEON_SIZE_X - WALL_MARGIN and 
        WALL_MARGIN <= new_z <= DUNGEON_SIZE_Z - WALL_MARGIN):
        blocked = False
        for ob in obstacles:
            dxo = new_x - ob['pos'][0]
            dzo = new_z - ob['pos'][1]
            if dxo*dxo + dzo*dzo < (PLAYER_RADIUS + ob['radius'])**2:
                blocked = True
                break
        if not blocked:
            player['pos'][0] = new_x
            player['pos'][2] = new_z

    # Manual rotation with Q/E (always honored)
    if keys_pressed.get(b'q'):
        player['rotation_y'] = (player['rotation_y'] + PLAYER_ROTATE_ANGLE) % 360.0
    if keys_pressed.get(b'e'):
        player['rotation_y'] = (player['rotation_y'] - PLAYER_ROTATE_ANGLE) % 360.0

    # Removed post-fire camera alignment (no aim assist)
    if camera_mode==CAMERA_MODE_FIRST_PERSON:
        if special_keys_pressed.get(GLUT_KEY_UP): 
            player['rotation_x']=max(-89.0,player['rotation_x']-PLAYER_ROTATE_ANGLE*0.7)
        if special_keys_pressed.get(GLUT_KEY_DOWN): 
            player['rotation_x']=min(89.0,player['rotation_x']+PLAYER_ROTATE_ANGLE*0.7)
    elif camera_mode==CAMERA_MODE_THIRD_PERSON:
        if special_keys_pressed.get(GLUT_KEY_UP): 
            tp_camera_pitch=max(-89.0,tp_camera_pitch-PLAYER_ROTATE_ANGLE*0.7)
        if special_keys_pressed.get(GLUT_KEY_DOWN): 
            tp_camera_pitch=min(0.0,tp_camera_pitch+PLAYER_ROTATE_ANGLE*0.7)
        if special_keys_pressed.get(GLUT_KEY_LEFT): 
            tp_camera_yaw_offset-=PLAYER_ROTATE_ANGLE
        if special_keys_pressed.get(GLUT_KEY_RIGHT): 
            tp_camera_yaw_offset+=PLAYER_ROTATE_ANGLE
    if player['shoot_cooldown']>0: 
        player['shoot_cooldown']-=delta_time
    
def update_enemies(delta_time):
    """Spawn/move enemies, avoid obstacles, and shoot at the player with cooldowns."""
    global player,game_state,enemy_anim_time
    enemy_anim_time += delta_time
    level_conf=level_configs[current_level]
    max_c=level_conf.get('max_concurrent',1)
    if len(enemies)<max_c and enemies_spawned_this_level<level_conf['total_enemies']: 
        spawn_enemy()
    for enemy in list(enemies):
        dist_player=distance_3d([player['pos'][0],player['pos'][1],player['pos'][2]],[enemy['pos'][0],enemy['pos'][1],enemy['pos'][2]])
        dir_to_p_vec=[player['pos'][0]-enemy['pos'][0],0,player['pos'][2]-enemy['pos'][2]]
        enemy['rotation_y']=math.degrees(math.atan2(dir_to_p_vec[0],dir_to_p_vec[2]))
        if dist_player > ENEMY_MIN_DISTANCE_FROM_PLAYER:
            dir_norm=normalize_vector(dir_to_p_vec)
            move_dist=enemy['speed']*delta_time
            nx = enemy['pos'][0]+dir_norm[0]*move_dist
            nz = enemy['pos'][2]+dir_norm[2]*move_dist
            # obstacle avoidance: stop if colliding simple radius
            can_move = True
            for ob in obstacles:
                dxo = nx - ob['pos'][0]
                dzo = nz - ob['pos'][1]
                if dxo*dxo + dzo*dzo < (enemy['collision_radius'] + ob['radius'])**2:
                    can_move = False
                    break
            if can_move:
                enemy['pos'][0]=nx
                enemy['pos'][2]=nz
        er=enemy['collision_radius']
        enemy['pos'][0]=max(er,min(enemy['pos'][0],DUNGEON_SIZE_X-er))
        enemy['pos'][2]=max(er,min(enemy['pos'][2],DUNGEON_SIZE_Z-er))
        if enemy['shoot_cooldown']>0: enemy['shoot_cooldown']-=delta_time
        elif dist_player < 30.0:
            enemy['shoot_cooldown']=enemy['reload_time']
            player_center_y = player['pos'][1] - PLAYER_BODY_Y_OFFSET + PLAYER_TOTAL_HEIGHT/2
            target_pos=[player['pos'][0],player_center_y,player['pos'][2]]
            
            enemy_face_center_y = enemy['pos'][1]
            gun_len_for_offset = 0.2 * enemy['model_height']
            s_yaw_e=math.sin(math.radians(enemy['rotation_y']))
            c_yaw_e=math.cos(math.radians(enemy['rotation_y']))

            start_x_e = enemy['pos'][0] + s_yaw_e * gun_len_for_offset
            start_z_e = enemy['pos'][2] + c_yaw_e * gun_len_for_offset 
            enemy_bullet_start_pos=[start_x_e,enemy_face_center_y,start_z_e]
            enemy_bullet_dir=normalize_vector([target_pos[0]-start_x_e,target_pos[1]-enemy_face_center_y,target_pos[2]-start_z_e])
            create_bullet(enemy_bullet_start_pos,enemy_bullet_dir,'ENEMY',enemy['damage'])

def update_bullets(delta_time):
    """Integrate bullets, cull by bounds/lifespan, and resolve hits against
    enemies or the player."""
    global player, game_state, enemies_killed_this_level, boss_entity, win_score_recorded
    
    for bullet in list(bullets):

        bullet['pos'][0] += bullet['dir'][0] * BULLET_SPEED * delta_time
        bullet['pos'][1] += bullet['dir'][1] * BULLET_SPEED * delta_time
        bullet['pos'][2] += bullet['dir'][2] * BULLET_SPEED * delta_time
        bullet['lifespan'] -= delta_time
        
        if bullet['lifespan'] <= 0 or not (
            -BULLET_RADIUS < bullet['pos'][0] < DUNGEON_SIZE_X + BULLET_RADIUS and
            -BULLET_RADIUS < bullet['pos'][1] < WALL_HEIGHT + BULLET_RADIUS and
            -BULLET_RADIUS < bullet['pos'][2] < DUNGEON_SIZE_Z + BULLET_RADIUS):
            if bullet in bullets:
                bullets.remove(bullet)
            continue
            
        if bullet['owner'] == 'PLAYER':
            for enemy in list(enemies):
                bullet_to_enemy = [
                    enemy['pos'][0] - bullet['pos'][0],
                    enemy['pos'][1] - bullet['pos'][1],
                    enemy['pos'][2] - bullet['pos'][2]
                ]
                
                dist = math.sqrt(sum(x*x for x in bullet_to_enemy))
                
                if dist < enemy['collision_radius'] * 1.5:
                    if bullet in bullets:
                        bullets.remove(bullet)
                    enemy['health'] -= 1
                    if enemy['health'] <= 0:
                        handle_enemy_death(enemy)
                    break
                    
        elif bullet['owner'] == 'ENEMY':
            bullet_to_player = [
                player['pos'][0] - bullet['pos'][0],
                (player['pos'][1] - PLAYER_BODY_Y_OFFSET + PLAYER_TOTAL_HEIGHT/2) - bullet['pos'][1],
                player['pos'][2] - bullet['pos'][2]
            ]
            
            dist = math.sqrt(sum(x*x for x in bullet_to_player))
            
            if dist < PLAYER_RADIUS * 1.5:
                if bullet in bullets:
                    bullets.remove(bullet)
                handle_player_hit(bullet['damage'])

def handle_enemy_death(enemy):
    """Remove a dead enemy, award points (with score perk), update perk counters."""
    global enemies, boss_entity, enemies_killed_this_level, player
    score_mult = 2 if player['score_perk_time_left'] > 0 else 1
    player['score'] += enemy['points'] * score_mult
    if enemy in enemies:
        enemies.remove(enemy)
    if enemy is boss_entity:
        boss_entity = None
    enemies_killed_this_level += 1
    update_perks()

def handle_player_hit(damage):
    """Apply damage to the player unless in cheat mode. On death, record score and
    start a game-over transition."""
    global player, game_state
    if cheat_mode:
        return  # godmode in cheat
    player['health'] -= damage
    if player['health'] <= 0 and game_state == STATE_PLAYING:
        player['health'] = 0
        # Record score on death before resetting
        record_high_score(player['score'])
        start_transition(STATE_GAME_OVER_TRANSITION, [1.0, 0.0, 0.0])

def check_level_completion():
    global game_state, win_score_recorded
    level_conf=level_configs[current_level]
    if enemies_spawned_this_level>=level_conf['total_enemies'] and not enemies and game_state==STATE_PLAYING:
        if current_level==max_levels: 
            game_state=STATE_YOU_WIN
            record_high_score(player['score'])
        else: 
            start_transition(STATE_LEVEL_TRANSITION,[0.0,1.0,0.0])

def start_transition(target_state,color):
    global game_state,transition_timer,transition_color,next_game_state_after_transition
    game_state=target_state
    transition_timer=TRANSITION_DURATION
    transition_color=color
    if target_state==STATE_LEVEL_TRANSITION: 
        next_game_state_after_transition=STATE_PLAYING 
    elif target_state==STATE_GAME_OVER_TRANSITION: 
        next_game_state_after_transition=STATE_PLAYING

def update_game_state(delta_time):
    """Main per-frame state machine: updates during play, and counts down
    transitions between levels or after death."""
    global player, transition_timer, current_level, cheat_fire_timer
    if game_state==STATE_PLAYING: 
        update_player(delta_time)
        update_enemies(delta_time)
        # Cheat auto-fire: periodically shoot at nearest enemy
        global cheat_fire_timer
        if cheat_mode and enemies:
            cheat_fire_timer += delta_time
            if cheat_fire_timer >= CHEAT_SHOOT_INTERVAL:
                cheat_fire_timer = 0.0
                # find nearest enemy on XZ
                px, pz = player['pos'][0], player['pos'][2]
                nearest = None
                nearest_d2 = 1e18
                for e in enemies:
                    dx = e['pos'][0] - px
                    dz = e['pos'][2] - pz
                    d2 = dx*dx + dz*dz
                    if d2 < nearest_d2:
                        nearest = e
                        nearest_d2 = d2
                if nearest is not None:
                    # Smoothly rotate player to face the target for realism
                    target_yaw = math.degrees(math.atan2(nearest['pos'][0] - player['pos'][0], nearest['pos'][2] - player['pos'][2]))
                    # Normalize angles to [-180,180] difference
                    cur_yaw = player['rotation_y']
                    diff = ((target_yaw - cur_yaw + 180.0) % 360.0) - 180.0
                    rot_speed_deg_per_sec = 180.0  # turn speed while cheating
                    step = max(-rot_speed_deg_per_sec * delta_time, min(rot_speed_deg_per_sec * delta_time, diff))
                    player['rotation_y'] = (cur_yaw + step) % 360.0
                    # Ensure bullet direction aligns to current rotation (gun and rotation synced)
                    # compute direction from player's gun tip toward enemy center
                    yaw_rad = math.radians(player['rotation_y'])
                    gun_base_offset = 0.35 * PLAYER_TOTAL_HEIGHT
                    gun_length = PLAYER_GUN_LENGTH
                    shoulder_height = PLAYER_LEG_LENGTH + PLAYER_TORSO_HEIGHT * 0.8
                    gun_y = player['pos'][1] - PLAYER_BODY_Y_OFFSET + shoulder_height
                    dir_x = math.sin(yaw_rad)
                    dir_z = math.cos(yaw_rad)
                    gun_base_x = player['pos'][0] + dir_x * gun_base_offset
                    gun_base_z = player['pos'][2] + dir_z * gun_base_offset
                    tip_world_x = gun_base_x + dir_x * gun_length
                    tip_world_y = gun_y
                    tip_world_z = gun_base_z + dir_z * gun_length
                    to_enemy = [nearest['pos'][0]-tip_world_x, (nearest['pos'][1]-nearest['model_height']/2 + nearest['model_height']*0.5)-tip_world_y, nearest['pos'][2]-tip_world_z]
                    fire_dir = normalize_vector(to_enemy)
                    create_bullet([tip_world_x, tip_world_y, tip_world_z], fire_dir, 'PLAYER', 1)
        update_bullets(delta_time)
        check_level_completion()
    elif game_state==STATE_LEVEL_TRANSITION:
        global transition_timer, current_level
        transition_timer-=delta_time
        if transition_timer<=0: 
            current_level+=1
            init_level(current_level)
    elif game_state==STATE_GAME_OVER_TRANSITION:
        transition_timer-=delta_time
        if transition_timer<=0: 
            player['health']=PLAYER_MAX_HEALTH
            player['score']=0
            init_level(current_level)

def update_perks():
    """Update perk availability based on enemy kills"""
    global player
    
    # Track kills for each perk type
    player['kills_for_health_perk'] += 1
    player['kills_for_score_perk'] += 1
    player['kills_for_gun_perk'] += 1
    
    # Health perk becomes available every 5 kills
    if player['kills_for_health_perk'] >= 3:
        player['health_perk_available'] = True
    
    # Score multiplier perk becomes available every 3 kills
    if player['kills_for_score_perk'] >= 4:
        player['score_perk_available'] = True
    
    # Rapid fire perk becomes available every 4 kills
    if player['kills_for_gun_perk'] >= 5:
        player['gun_perk_available'] = True

# --- Drawing Functions ---
def draw_text(x,y,text,r=1,g=1,b=1,font=GLUT_BITMAP_HELVETICA_18): 
    glColor3f(r,g,b)
    glRasterPos2f(x,y)
    [glutBitmapCharacter(font,ord(c)) for c in text]

def draw_filled_rect(x, y, w, h, r, g, b, a=1.0):
    glColor4f(r, g, b, a)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()

def draw_text_shadowed(x, y, text, r=1, g=1, b=1, font=GLUT_BITMAP_HELVETICA_18):
    # Enhanced drop shadow with glow effect
    glColor3f(0,0,0)
    glRasterPos2f(x+3, y-3)
    [glutBitmapCharacter(font,ord(c)) for c in text]
    glColor3f(0.1,0.1,0.1)
    glRasterPos2f(x+2, y-2)
    [glutBitmapCharacter(font,ord(c)) for c in text]
    glColor3f(r,g,b)
    glRasterPos2f(x, y)
    [glutBitmapCharacter(font,ord(c)) for c in text]

def draw_large_text(x, y, text, r=1, g=1, b=1):
    # Draw large title text with multiple shadow layers
    glColor3f(0,0,0)
    glRasterPos2f(x+4, y-4)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.1,0.1,0.1)
    glRasterPos2f(x+3, y-3)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.2,0.2,0.2)
    glRasterPos2f(x+2, y-2)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(r,g,b)
    glRasterPos2f(x, y)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]

def draw_giant_title(x, y, text, r=1, g=1, b=1):
    # Draw ultra-large title text with massive dramatic shadows
    # Multiple shadow layers for depth
    glColor3f(0,0,0)
    glRasterPos2f(x+8, y-8)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.05,0.05,0.05)
    glRasterPos2f(x+7, y-7)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.1,0.1,0.1)
    glRasterPos2f(x+6, y-6)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.15,0.15,0.15)
    glRasterPos2f(x+5, y-5)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.2,0.2,0.2)
    glRasterPos2f(x+4, y-4)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.25,0.25,0.25)
    glRasterPos2f(x+3, y-3)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(0.3,0.3,0.3)
    glRasterPos2f(x+2, y-2)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    # Main text with slight glow effect
    glColor3f(r*1.1, g*1.1, b*1.1)
    glRasterPos2f(x+1, y+1)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]
    glColor3f(r,g,b)
    glRasterPos2f(x, y)
    [glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(c)) for c in text]

def get_text_width(text, font=GLUT_BITMAP_HELVETICA_18):
    # Calculate text width for centering (estimated)
    # Approximate character width for HELVETICA_18 is about 10 pixels
    return len(text) * 10

def ui_reset_buttons():
    del ui_buttons[:]

def ui_add_button(label, x, y, w, h, action, color=(0.2,0.2,0.2), text_color=(1,1,1)):
    # Hover detection
    is_hover = (x <= mouse_pos['x'] <= x + w) and (y <= mouse_pos['y'] <= y + h)
    bg = [color[0], color[1], color[2]]
    if is_hover:
        bg = [min(1.0, bg[0]*1.25), min(1.0, bg[1]*1.25), min(1.0, bg[2]*1.25)]
    # Button background
    draw_filled_rect(x, y, w, h, bg[0], bg[1], bg[2], 0.92 if is_hover else 0.85)
    # Simple border
    glColor3f(1,1,1)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()
    # Text centered-ish
    text_w = len(label) * 9
    text_h = 18
    draw_text(x + (w - text_w) / 2, y + (h - text_h) / 2 + 6, label, text_color[0], text_color[1], text_color[2])
    ui_buttons.append({'label': label, 'x': x, 'y': y, 'w': w, 'h': h, 'action': action})

def point_in_rect(px, py, rect):
    return rect['x'] <= px <= rect['x'] + rect['w'] and rect['y'] <= py <= rect['y'] + rect['h']

def record_high_score(score):
    """Append a score to HoF (guarding duplicates), keep top 3 by score then recency."""
    global hof_seq, hof_records, current_session_score_recorded
    if score <= 0 or current_session_score_recorded:
        return
    current_session_score_recorded = True
    hof_seq += 1
    hof_records.append({'score': int(score), 'seq': hof_seq})
    # Keep only the top 3 by score, break ties by recency (higher seq wins)
    hof_records.sort(key=lambda r: (r['score'], r['seq']), reverse=True)
    del hof_records[3:]

def top_three_scores():
    """Return the already-sorted, already-trimmed top 3 score records."""
    return hof_records

def draw_cylinder(base_r,top_r,height,slices,stacks,color):
    global glu_quadric
    glColor3fv(color)
    glPushMatrix()

    glRotatef(-90,1,0,0) 
    gluCylinder(glu_quadric,base_r,top_r,height,slices,stacks)
    gluDisk(glu_quadric,0,base_r,slices,1)
    glTranslatef(0,0,height)
    gluDisk(glu_quadric,0,top_r,slices,1)
    glPopMatrix()

def draw_tapered_cylinder(base_radius, top_radius, height, color):
    global glu_quadric
    glColor3fv(color)
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    gluCylinder(glu_quadric, base_radius, top_radius, height, 20, 8)
    # Base cap
    gluDisk(glu_quadric, 0, base_radius, 20, 8)
    # Top cap
    glTranslatef(0, 0, height)
    gluDisk(glu_quadric, 0, top_radius, 20, 8)
    glPopMatrix()

def draw_player():
    """Render the player model using simple GL primitives, positioned at origin.
    The caller is responsible for transforming to the player's world position."""
    glPushMatrix()
    
    # Scale everything relative to PLAYER_TOTAL_HEIGHT
    model_scale = PLAYER_TOTAL_HEIGHT
    
    # Body positioning constants
    torso_height = 0.45 * model_scale
    head_radius = 0.15 * model_scale
    
    # Body (centered at origin)
    glPushMatrix()
    glTranslatef(0, PLAYER_LEG_LENGTH + torso_height/2, 0)
    glColor3f(0.5, 0.5, 0.0)
    glScalef(0.3 * model_scale, torso_height, 0.25 * model_scale)
    glutSolidCube(1.0)
    glPopMatrix()

    # Head (directly above body)
    glPushMatrix()
    glTranslatef(0, PLAYER_LEG_LENGTH + torso_height + head_radius, 0)
    glColor3f(0.8, 0.6, 0.4)
    glutSolidSphere(head_radius, 20, 20)
    # Visor
    glPushMatrix()
    glTranslatef(0, 0.02 * PLAYER_TOTAL_HEIGHT, 0.11 * PLAYER_TOTAL_HEIGHT)
    glColor3f(0.1, 0.8, 0.9)
    glScalef(0.18 * PLAYER_TOTAL_HEIGHT, 0.09 * PLAYER_TOTAL_HEIGHT, 0.02 * PLAYER_TOTAL_HEIGHT)
    glutSolidCube(1.0)
    glPopMatrix()
    glPopMatrix()

    # Arms (at shoulder height - moved forward)
    shoulder_height = PLAYER_LEG_LENGTH + torso_height * 0.8
    
    # Left arm - moved forward
    glPushMatrix()
    glTranslatef(-0.15 * model_scale, shoulder_height, 0.15 * model_scale)
    glRotatef(15, 0, 1, 0)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(0.05 * model_scale, 0.04 * model_scale, PLAYER_ARM_LENGTH * 0.7, 8, 1, (0.8, 0.6, 0.4))
    glPopMatrix()

    # Right arm - moved forward
    glPushMatrix()
    glTranslatef(0.15 * model_scale, shoulder_height, 0.15 * model_scale)
    glRotatef(-15, 0, 1, 0)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(0.05 * model_scale, 0.04 * model_scale, PLAYER_ARM_LENGTH * 0.7, 8, 1, (0.8, 0.6, 0.4))
    glPopMatrix()

    # Gun (centered between arms and moved forward) with muzzle
    glPushMatrix()
    glTranslatef(0, shoulder_height, 0.35 * model_scale)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(0.05 * model_scale, 0.03 * model_scale, PLAYER_GUN_LENGTH, 8, 1, (0.3, 0.3, 0.3))
    # Muzzle highlight
    glTranslatef(0, 0, PLAYER_GUN_LENGTH)
    glColor3f(1.0, 0.8, 0.2)
    glutSolidSphere(0.02 * model_scale, 10, 10)
    glPopMatrix()

    # Backpack
    glPushMatrix()
    glTranslatef(0, PLAYER_LEG_LENGTH + torso_height*0.4, -0.18 * model_scale)
    glColor3f(0.2, 0.2, 0.25)
    glScalef(0.20 * model_scale, 0.35 * model_scale, 0.12 * model_scale)
    glutSolidCube(1.0)
    glPopMatrix()

    # Legs (starting from bottom of body)
    leg_start_height = PLAYER_LEG_LENGTH
    
    # Left leg
    glPushMatrix()
    glTranslatef(-0.1 * model_scale, leg_start_height, 0)
    glRotatef(180, 1, 0, 0)
    draw_cylinder(0.06 * model_scale, 0.05 * model_scale, PLAYER_LEG_LENGTH, 8, 1, (0.3, 0.3, 0.8))
    glPopMatrix()

    # Right leg
    glPushMatrix()
    glTranslatef(0.1 * model_scale, leg_start_height, 0)
    glRotatef(180, 1, 0, 0)
    draw_cylinder(0.06 * model_scale, 0.05 * model_scale, PLAYER_LEG_LENGTH, 8, 1, (0.3, 0.3, 0.8))
    glPopMatrix()

    glPopMatrix()

def draw_wolf(total_h, body_c, leg_c, face_c, gun_c, variant=1):
    """Render a stylized enemy at origin using basic shapes. Variant subtly changes look."""

    body_width = total_h * 0.35
    body_height = total_h * 0.35
    body_depth = total_h * 0.7
    face_size = total_h * 0.25
    leg_len = total_h * 0.4
    leg_r = total_h * 0.04
    gun_len = total_h * 0.3
    gun_r = total_h * 0.04

    darkened_body_c = [c * 0.7 for c in body_c]
    darkened_face_c = [c * 0.7 for c in face_c]
    black_legs_c = [0.1, 0.1, 0.1]

    # Body positioning
    body_center_y = leg_len + body_height/2

    # Body
    glPushMatrix()
    glTranslatef(0, body_center_y, 0)
    # Variant-based body tint
    tint = [1.0,1.0,1.0]
    if variant==2:
        tint=[1.1,0.95,0.95]
    elif variant==3:
        tint=[0.95,0.95,1.1]
    glColor3f(darkened_body_c[0]*tint[0], darkened_body_c[1]*tint[1], darkened_body_c[2]*tint[2])
    glScalef(body_width, body_height, body_depth)
    glutSolidCube(1.0)
    glPopMatrix()

    # Face
    face_center_y = body_center_y
    face_center_z = body_depth/2 + face_size/4
    glPushMatrix()
    glTranslatef(0, face_center_y, face_center_z)
    glColor3fv(darkened_face_c)
    glScalef(face_size, face_size, face_size * 0.5)
    glutSolidCube(1.0)
    glPopMatrix()

    # Muzzle (protruding cube)
    glPushMatrix()
    glTranslatef(0, face_center_y - face_size*0.12, face_center_z + face_size*0.35)
    glColor3f(darkened_face_c[0]*1.1, darkened_face_c[1]*1.1, darkened_face_c[2]*1.1)
    glScalef(face_size*0.55, face_size*0.35, face_size*0.4)
    glutSolidCube(1.0)
    glPopMatrix()

    # Eyes (white spheres with black pupils)
    eye_offset_x = face_size*0.18
    eye_y = face_center_y + face_size*0.10
    eye_z = face_center_z + face_size*0.32
    eye_r = face_size*0.07
    pupil_r = eye_r*0.45
    for sx in (-1, 1):
        glPushMatrix()
        glTranslatef(sx*eye_offset_x, eye_y, eye_z)
        glColor3f(1.0, 1.0, 1.0)
        glutSolidSphere(eye_r, 12, 12)
        glColor3f(0.0, 0.0, 0.0)
        glTranslatef(0, 0, pupil_r*0.3)
        glutSolidSphere(pupil_r, 10, 10)
        glPopMatrix()

    # Ears (tapered cones on head top)
    ear_r_base = face_size*0.12
    ear_r_top = ear_r_base*0.25
    ear_h = face_size*(0.6 if variant!=3 else 0.8)
    ear_y = face_center_y + face_size*0.6
    ear_z = face_center_z - face_size*0.20
    for sx in (-1, 1):
        glPushMatrix()
        glTranslatef(sx*face_size*0.30, ear_y, ear_z)
        glRotatef(-90, 1, 0, 0)
        draw_tapered_cylinder(ear_r_base, ear_r_top, ear_h, darkened_face_c)
        glPopMatrix()

    # Gun
    gun_start_y = face_center_y
    gun_start_z = face_center_z + face_size/4
    glPushMatrix()
    glTranslatef(0, gun_start_y, gun_start_z)
    glRotatef(90, 1, 0, 0)
    draw_cylinder(gun_r, gun_r * 0.8, gun_len, 8, 1, gun_c)
    glPopMatrix()

    # Tail (tapered cylinder at rear)
    tail_r_base = total_h * 0.05
    tail_r_top = tail_r_base * 0.4
    tail_len = total_h * (0.5 if variant!=2 else 0.7)
    glPushMatrix()
    glTranslatef(0, body_center_y + body_height*0.05, -body_depth*0.55)
    glRotatef(60, 1, 0, 0)
    draw_tapered_cylinder(tail_r_base, tail_r_top, tail_len, [c*0.6 for c in body_c])
    glPopMatrix()

    # Back ridge (small plates along spine)
    ridge_count = 4 if variant==1 else (6 if variant==3 else 3)
    for i in range(ridge_count):
        t = (i + 0.5) / ridge_count
        rz = body_depth*(t - 0.5) * 0.8
        glPushMatrix()
        glTranslatef(0, body_center_y + body_height*0.45, rz)
        glColor3f(0.1, 0.1, 0.1)
        glScalef(body_width*0.15, body_height*0.1, body_depth*0.10)
        glutSolidCube(1.0)
        glPopMatrix()

    # Accent stripes on sides
    stripe_y = body_center_y
    for sx in (-1, 1):
        for i in range(2):
            zf = [-0.15, 0.25][i]
            glPushMatrix()
            glTranslatef(sx*body_width*0.55, stripe_y, body_depth*zf)
            glColor3f(darkened_body_c[0]*0.8, darkened_body_c[1]*0.8, darkened_body_c[2]*0.8)
            glScalef(body_width*0.05, body_height*0.6, body_depth*0.15)
            glutSolidCube(1.0)
            glPopMatrix()

    # Legs
    leg_attach_y = body_center_y - body_height/2
    front_leg_z = body_depth * 0.3
    rear_leg_z = -body_depth * 0.3
    leg_x = body_width * 0.4

    # Front Right Leg
    glPushMatrix()
    glTranslatef(leg_x, leg_attach_y, front_leg_z)
    glRotatef(180, 1, 0, 0)
    draw_tapered_cylinder(leg_r, leg_r * 0.7, leg_len, black_legs_c)
    glPopMatrix()

    # Front Left Leg
    glPushMatrix()
    glTranslatef(-leg_x, leg_attach_y, front_leg_z)
    glRotatef(180, 1, 0, 0)
    draw_tapered_cylinder(leg_r, leg_r * 0.7, leg_len, black_legs_c)
    glPopMatrix()

    # Rear Right Leg
    glPushMatrix()
    glTranslatef(leg_x, leg_attach_y, rear_leg_z)
    glRotatef(180, 1, 0, 0)
    draw_tapered_cylinder(leg_r, leg_r * 0.7, leg_len, black_legs_c)
    glPopMatrix()

    # Rear Left Leg
    glPushMatrix()
    glTranslatef(-leg_x, leg_attach_y, rear_leg_z)
    glRotatef(180, 1, 0, 0)
    draw_tapered_cylinder(leg_r, leg_r * 0.7, leg_len, black_legs_c)
    glPopMatrix()


def draw_dungeon():
    """Render floor, walls and obstacles with colors based on the current theme group."""
    # Define color schemes based on level (Earth, Mud, Heaven, Hell)
    if current_level <= 3:
        # Earth (lush greens)
        tile_color1 = (0.40, 0.80, 0.40)
        tile_color2 = (0.20, 0.55, 0.25)
        wall_color1 = (0.12, 0.28, 0.12)
        wall_color2 = (0.16, 0.36, 0.18)
    elif current_level <= 6:
        # Mud (rich browns, clay, ochre)
        tile_color1 = (0.62, 0.45, 0.28)
        tile_color2 = (0.45, 0.30, 0.18)
        wall_color1 = (0.35, 0.18, 0.12)
        wall_color2 = (0.42, 0.22, 0.15)
    elif current_level <= 9:
        # Heaven (soft blues/whites)
        tile_color1 = (0.80, 0.88, 1.00)
        tile_color2 = (0.65, 0.80, 0.95)
        wall_color1 = (0.60, 0.80, 0.95)
        wall_color2 = (0.72, 0.88, 1.00)
    else:
        # Hell (crimson/embers)
        tile_color1 = (0.70, 0.20, 0.20)
        tile_color2 = (0.45, 0.10, 0.10)
        wall_color1 = (0.55, 0.05, 0.06)
        wall_color2 = (0.68, 0.12, 0.10)

    # Floor with checkered pattern
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    for x in range(int(DUNGEON_SIZE_X/TILE_SIZE)):
        for z in range(int(DUNGEON_SIZE_Z/TILE_SIZE)):
            # Alternate between colors
            if (x + z) % 2 == 0:
                glColor3f(*tile_color1)
            else:
                glColor3f(*tile_color2)
            
            x1 = x * TILE_SIZE
            x2 = (x + 1) * TILE_SIZE
            z1 = z * TILE_SIZE
            z2 = (z + 1) * TILE_SIZE
            
            glVertex3f(x1, 0, z1)
            glVertex3f(x2, 0, z1)
            glVertex3f(x2, 0, z2)
            glVertex3f(x1, 0, z2)
    glEnd()

    # Walls with alternating pattern and subtle top trim
    wall_sections = 20  # Number of wall sections
    section_length = DUNGEON_SIZE_X / wall_sections
    
    for i in range(wall_sections):
        current_wall_color = wall_color1 if (i % 2 == 0) else wall_color2
        # North wall
        glColor3f(*current_wall_color)
            
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glVertex3f(i * section_length, 0, 0)
        glVertex3f((i + 1) * section_length, 0, 0)
        glVertex3f((i + 1) * section_length, WALL_HEIGHT, 0)
        glVertex3f(i * section_length, WALL_HEIGHT, 0)
        glEnd()
        # Top trim line
        glBegin(GL_QUADS)
        glColor3f(0.9,0.9,0.9)
        glVertex3f(i * section_length, WALL_HEIGHT*0.98, 0)
        glVertex3f((i + 1) * section_length, WALL_HEIGHT*0.98, 0)
        glVertex3f((i + 1) * section_length, WALL_HEIGHT, 0)
        glVertex3f(i * section_length, WALL_HEIGHT, 0)
        glEnd()
        
        # South wall
        glColor3f(*current_wall_color)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, -1)
        glVertex3f(i * section_length, 0, DUNGEON_SIZE_Z)
        glVertex3f(i * section_length, WALL_HEIGHT, DUNGEON_SIZE_Z)
        glVertex3f((i + 1) * section_length, WALL_HEIGHT, DUNGEON_SIZE_Z)
        glVertex3f((i + 1) * section_length, 0, DUNGEON_SIZE_Z)
        glEnd()
        
        # East and West walls
        glColor3f(*current_wall_color)
        glBegin(GL_QUADS)
        glNormal3f(1, 0, 0)
        glVertex3f(0, 0, i * section_length)
        glVertex3f(0, WALL_HEIGHT, i * section_length)
        glVertex3f(0, WALL_HEIGHT, (i + 1) * section_length)
        glVertex3f(0, 0, (i + 1) * section_length)
        glEnd()
        
        glColor3f(*current_wall_color)
        glBegin(GL_QUADS)
        glNormal3f(-1, 0, 0)
        glVertex3f(DUNGEON_SIZE_X, 0, i * section_length)
        glVertex3f(DUNGEON_SIZE_X, 0, (i + 1) * section_length)
        glVertex3f(DUNGEON_SIZE_X, WALL_HEIGHT, (i + 1) * section_length)
        glVertex3f(DUNGEON_SIZE_X, WALL_HEIGHT, i * section_length)
        glEnd()

    # Obstacles
    for ob in obstacles:
        glPushMatrix()
        glTranslatef(ob['pos'][0], 0, ob['pos'][1])
        glColor3fv(ob['color'])
        if ob['shape']=='cyl':
            draw_cylinder(ob['radius'], ob['radius'], ob['height'], 16, 1, ob['color'])
        else:
            glPushMatrix()
            glTranslatef(0, ob['height']/2, 0)
            glScalef(ob['radius']*2, ob['height'], ob['radius']*2)
            glutSolidCube(1.0)
            glPopMatrix()
        glPopMatrix()

def draw_ui():
    """Render HUD or menu overlays in orthographic projection and manage UI buttons."""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0,SCREEN_WIDTH,0,SCREEN_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    # HUD or Menus
    if game_state==STATE_PLAYING:
        draw_text(10,SCREEN_HEIGHT-30,f"Health: {player['health']}/{PLAYER_MAX_HEALTH}",1,0.2,0.2)
        draw_text(10,SCREEN_HEIGHT-60,f"Score: {player['score']}",1,1,0.2)
        draw_text(SCREEN_WIDTH-200,SCREEN_HEIGHT-30,f"Level: {current_level}",0.8,0.8,0.8)
        if cheat_mode:
            draw_text(SCREEN_WIDTH-220,SCREEN_HEIGHT-60,"Cheat Mode: ON",1.0,0.6,0.2)
        perk_y=SCREEN_HEIGHT-90
        if player['health_perk_available']: 
            draw_text(10,perk_y,"Health Perk Ready!(H)",0,1,0)
            perk_y-=25
        if player['score_perk_available']:
            draw_text(10,perk_y,"Score Perk Ready!(F)",1,1,0)
            perk_y-=25
        if player['gun_perk_available']: 
            draw_text(10,perk_y,"Gun Perk Ready!(G)",1,0.5,0)
            perk_y-=25
        active_perk_y=SCREEN_HEIGHT-90
        if player['score_perk_time_left']>0:
            rem=int(player['score_perk_time_left'])
            draw_text(SCREEN_WIDTH-250,active_perk_y,f"Score x2: {rem}s",1,1,0)
            active_perk_y-=25
        if player['gun_perk_time_left']>0:
            rem=int(player['gun_perk_time_left'])
            draw_text(SCREEN_WIDTH-250,active_perk_y,f"Rapid Fire: {rem}s",1,0.5,0)
            active_perk_y-=25
    elif game_state==STATE_PAUSED:
        # Dim background
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0,0.6)
        ui_reset_buttons()
        panel_w, panel_h = 420, 280
        px = (SCREEN_WIDTH - panel_w)//2
        py = (SCREEN_HEIGHT - panel_h)//2
        draw_filled_rect(px+6, py-6, panel_w, panel_h, *UI_COLORS['panel_shadow'])
        draw_filled_rect(px, py, panel_w, panel_h, *UI_COLORS['panel'], 0.95)
        draw_text_shadowed(px+20, py+panel_h-40, "Paused", *UI_COLORS['title'], GLUT_BITMAP_HELVETICA_18)
        btn_w, btn_h = 360, 48
        gap = 16
        bx = px + 30
        by = py + panel_h - 100
        ui_add_button('Resume', bx, by, btn_w, btn_h, action='pause_resume', color=UI_COLORS['btn_secondary'])
        by -= (btn_h + gap)
        ui_add_button('Retry Level', bx, by, btn_w, btn_h, action='pause_retry', color=UI_COLORS['btn_neutral'])
        by -= (btn_h + gap)
        ui_add_button('Return to Main Menu', bx, by, btn_w, btn_h, action='pause_to_main', color=UI_COLORS['btn_warn'])
        # Ensure we exit after drawing pause menu so nothing overrides it
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        return
    elif game_state==STATE_MAIN_MENU:
        ui_reset_buttons()
        # Dark atmospheric background
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,*UI_COLORS['bg_main_top'],1)
        # Subtle gradient overlay
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,*UI_COLORS['bg_main_bottom'],0.4)
        # Atmospheric border effect
        glColor3f(0.1,0.1,0.15)
        glBegin(GL_LINE_LOOP)
        glVertex2f(20, 20)
        glVertex2f(SCREEN_WIDTH-20, 20)
        glVertex2f(SCREEN_WIDTH-20, SCREEN_HEIGHT-20)
        glVertex2f(20, SCREEN_HEIGHT-20)
        glEnd()
        
        # Massive centered title
        title = '8bit Doom'
        title_width = get_text_width(title)
        title_x = (SCREEN_WIDTH - title_width) // 2
        title_y = SCREEN_HEIGHT - 200
        draw_giant_title(title_x, title_y, title, *UI_COLORS['accent_gold'])
        
        btn_w, btn_h = 380, 65
        bx = (SCREEN_WIDTH - btn_w)//2
        by = SCREEN_HEIGHT - 320
        ui_add_button('Start New Game', bx, by, btn_w, btn_h, action='menu_start', color=UI_COLORS['btn_primary'])
        by -= btn_h + 25
        ui_add_button('Select Level', bx, by, btn_w, btn_h, action='menu_select_level', color=UI_COLORS['btn_secondary'])
        by -= btn_h + 25
        ui_add_button('Hall Of Fame', bx, by, btn_w, btn_h, action='menu_hof', color=UI_COLORS['btn_neutral'])
        by -= btn_h + 25
        ui_add_button('Exit', bx, by, btn_w, btn_h, action='menu_exit', color=UI_COLORS['btn_warn'])
    elif game_state==STATE_LEVEL_SELECT:
        ui_reset_buttons()
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,*UI_COLORS['bg_main_top'],1)
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,*UI_COLORS['bg_main_bottom'],0.3)
        draw_text_shadowed(40, SCREEN_HEIGHT-80, 'Select Level', *UI_COLORS['title'], GLUT_BITMAP_HELVETICA_18)
        # Grid of 10 buttons
        cols = 5
        rows = 2
        btn_w, btn_h = 160, 60
        margin_x, margin_y = 40, 140
        gap_x, gap_y = 30, 30
        for i in range(10):
            col = i % cols
            row = i // cols
            x = margin_x + col * (btn_w + gap_x)
            y = SCREEN_HEIGHT - margin_y - row * (btn_h + gap_y)
            color = UI_COLORS['btn_primary'] if i<3 else (UI_COLORS['btn_secondary'] if i<6 else UI_COLORS['btn_neutral'])
            ui_add_button(f'Level {i+1}', x, y, btn_w, btn_h, action=f'level_{i+1}', color=color)
        # Back
        ui_add_button('Back', 40, 40, 140, 48, action='back_to_main', color=UI_COLORS['btn_neutral'])
    elif game_state==STATE_HALL_OF_FAME:
        ui_reset_buttons()
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,*UI_COLORS['bg_main_top'],1)
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,*UI_COLORS['bg_main_bottom'],0.3)
        draw_text_shadowed(40, SCREEN_HEIGHT-80, 'Hall Of Fame (Top 3)', *UI_COLORS['title'], GLUT_BITMAP_HELVETICA_18)
        top3 = top_three_scores()
        y = SCREEN_HEIGHT-140
        rank = 1
        if not top3:
            draw_text_shadowed(60, y, 'No scores yet. Play to set a record!', 1,1,0.6)
        else:
            for s in top3:
                draw_text_shadowed(60, y, f"{rank}. Score: {s.get('score',0)}", 1,1,0.8)
                y -= 40
                rank += 1
        ui_add_button('Back', 40, 40, 140, 48, action='back_to_main', color=UI_COLORS['btn_neutral'])
    # Transition overlays and end-state messages
    if game_state==STATE_LEVEL_TRANSITION:
        # Dim and show level completed message
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0,0.55)
        msg = "Level Completed"
        msg_w = get_text_width(msg)
        draw_text_shadowed((SCREEN_WIDTH - msg_w)//2, SCREEN_HEIGHT//2, msg, 0.9, 0.9, 0.9, GLUT_BITMAP_HELVETICA_18)
    elif game_state==STATE_GAME_OVER_TRANSITION:
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0,0.55)
        msg = "You died!"
        msg_w = get_text_width(msg)
        draw_text_shadowed((SCREEN_WIDTH - msg_w)//2, SCREEN_HEIGHT//2, msg, 1.0, 0.4, 0.4, GLUT_BITMAP_HELVETICA_18)
    elif game_state==STATE_YOU_WIN:
        draw_filled_rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0,0.55)
        win_msg = "Congratulations! Game Finished"
        win_w = get_text_width(win_msg)
        draw_text_shadowed((SCREEN_WIDTH - win_w)//2, SCREEN_HEIGHT//2 + 40, win_msg, 0.9, 1.0, 0.6, GLUT_BITMAP_HELVETICA_18)
        score_msg = f"Final Score: {player['score']}"
        score_w = get_text_width(score_msg)
        draw_text_shadowed((SCREEN_WIDTH - score_w)//2, SCREEN_HEIGHT//2 + 10, score_msg, 1,1,0.2, GLUT_BITMAP_HELVETICA_18)
        # Buttons
        ui_reset_buttons()
        btn_w, btn_h = 280, 54
        bx = (SCREEN_WIDTH - btn_w)//2
        by = SCREEN_HEIGHT//2 - 60
        ui_add_button('Return to Main Menu', bx, by, btn_w, btn_h, action='win_to_main', color=UI_COLORS['btn_secondary'])
        by -= (btn_h + 18)
        ui_add_button('Exit', bx, by, btn_w, btn_h, action='win_exit', color=UI_COLORS['btn_warn'])
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# --- GLUT Callbacks ---
def display():
    """Main frame render: set camera, lights, draw world/entities, then UI overlays."""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    if game_state in (STATE_PLAYING, STATE_LEVEL_TRANSITION, STATE_GAME_OVER_TRANSITION, STATE_YOU_WIN, STATE_PAUSED):
        player_base_x,player_base_y,player_base_z = player['pos']
        if camera_mode==CAMERA_MODE_FIRST_PERSON:
            eye_x=player_base_x
            eye_y=player_base_y-PLAYER_BODY_Y_OFFSET+PLAYER_EYE_HEIGHT_FROM_MODEL_BASE
            eye_z=player_base_z
            pitch_r=math.radians(player['rotation_x'])
            yaw_r=math.radians(player['rotation_y'])
            look_x=eye_x+math.sin(yaw_r)*math.cos(pitch_r)
            look_y=eye_y-math.sin(pitch_r)
            look_z=eye_z+math.cos(yaw_r)*math.cos(pitch_r)
            gluLookAt(eye_x,eye_y,eye_z,look_x,look_y,look_z,0,1,0)
        elif camera_mode==CAMERA_MODE_THIRD_PERSON:
            target_foc_y = player_base_y - PLAYER_BODY_Y_OFFSET + PLAYER_TOTAL_HEIGHT/2
            cam_x_off = tp_camera_distance * math.cos(math.radians(tp_camera_pitch)) * math.sin(math.radians(tp_camera_yaw_offset))
            cam_y_off = tp_camera_distance * math.sin(math.radians(-tp_camera_pitch))
            cam_z_off = -tp_camera_distance * math.cos(math.radians(tp_camera_pitch)) * math.cos(math.radians(tp_camera_yaw_offset))
            cam_x = player_base_x + cam_x_off
            cam_y = target_foc_y + cam_y_off
            cam_z = player_base_z + cam_z_off
            gluLookAt(cam_x, cam_y, cam_z, player_base_x, target_foc_y, player_base_z, 0, 1, 0)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    light_pos=[DUNGEON_SIZE_X/2,WALL_HEIGHT*1.8,DUNGEON_SIZE_Z/2,1.0]
    glLightfv(GL_LIGHT0,GL_POSITION,light_pos)
    glLightfv(GL_LIGHT0,GL_DIFFUSE,[0.9,0.9,0.8,1])
    glLightfv(GL_LIGHT0,GL_AMBIENT,[0.35,0.35,0.35,1])
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK,GL_AMBIENT_AND_DIFFUSE)
    if game_state in (STATE_PLAYING, STATE_LEVEL_TRANSITION, STATE_GAME_OVER_TRANSITION, STATE_YOU_WIN, STATE_PAUSED):
        draw_dungeon()
        if camera_mode == CAMERA_MODE_THIRD_PERSON:
            glPushMatrix()
            glTranslatef(player['pos'][0], player['pos'][1] - PLAYER_BODY_Y_OFFSET, player['pos'][2])
            glRotatef(player['rotation_y'], 0, 1, 0)
            draw_player()
            glPopMatrix()
        for enemy in enemies:
            glPushMatrix()
            bob = math.sin((enemy['pos'][0] + enemy['pos'][2]) * 0.2 + enemy_anim_time * 2.0) * (enemy['model_height'] * 0.02)
            glTranslatef(enemy['pos'][0],enemy['pos'][1]-enemy['model_height']/2 + bob,enemy['pos'][2])
            glRotatef(enemy['rotation_y'],0,1,0)
            # choose variant by enemy type/model height range
            variant = 1
            if enemy['model_height'] >= 7.0:
                variant = 3
            elif enemy['model_height'] >= 3.0:
                variant = 2
            draw_wolf(enemy['model_height'],enemy['color'],[c*0.8 for c in enemy['color']],[c*1.1 for c in enemy['color']],[0.1,0.1,0.1], variant)
            glPopMatrix()
    for bullet in bullets: 
        glPushMatrix()
        glTranslatef(bullet['pos'][0],bullet['pos'][1],bullet['pos'][2])
        glColor3fv(bullet['color'])
        glutSolidSphere(BULLET_RADIUS,6,6)
        glPopMatrix()
    if game_state==STATE_LEVEL_TRANSITION or game_state==STATE_GAME_OVER_TRANSITION:
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0,1,0,1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glColor4f(transition_color[0],transition_color[1],transition_color[2],0.85)
        glBegin(GL_QUADS)
        glVertex2f(0,0)
        glVertex2f(1,0)
        glVertex2f(1,1)
        glVertex2f(0,1)
        glEnd()
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    draw_ui()
    glutSwapBuffers()

def reshape(w,h):
    """Handle window resize and update orthographic UI extents."""
    global SCREEN_WIDTH,SCREEN_HEIGHT
    SCREEN_WIDTH,SCREEN_HEIGHT=w,h
    glViewport(0,0,w,h if h else 1)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0,float(w)/(h if h else 1),0.1,500.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def keyboard(key,x,y):
    """Keyboard input: gameplay controls, camera toggle, perks, pause, cheat and exit."""
    global camera_mode,player,game_state,win_score_recorded,cheat_mode,cheat_fire_timer
    k=key.lower()
    keys_pressed[k]=True

    # Global hotkeys
    if k == b'p':
        if game_state==STATE_PLAYING:
            game_state=STATE_PAUSED
        elif game_state==STATE_PAUSED:
            game_state=STATE_PLAYING
        return
    if k == b'c':
        # Toggle cheat mode (auto-fire + godmode)
        cheat_mode = not cheat_mode
        cheat_fire_timer = 0.0
        return

    # Ignore gameplay keys when not playing
    if game_state!=STATE_PLAYING:
        if game_state in (STATE_MAIN_MENU, STATE_LEVEL_SELECT, STATE_HALL_OF_FAME):
            if k == b'\x1b':
                glutLeaveMainLoop()
        return

    if k == b' ' and player['shoot_cooldown']<=0:
        player['shoot_cooldown'] = player['current_shoot_cooldown_time']
        # No manual aim assist before firing

        # Get player's current orientation
        yaw_rad = math.radians(player['rotation_y'])

        # Get local model space forward offset to the gun base and tip
        gun_base_offset = 0.35 * PLAYER_TOTAL_HEIGHT
        gun_length = PLAYER_GUN_LENGTH
        shoulder_height = PLAYER_LEG_LENGTH + PLAYER_TORSO_HEIGHT * 0.8
        gun_y = player['pos'][1] - PLAYER_BODY_Y_OFFSET + shoulder_height

        # Forward direction (player is facing)
        dir_x = math.sin(yaw_rad)
        dir_z = math.cos(yaw_rad)

        # Gun base world position
        gun_base_x = player['pos'][0] + dir_x * gun_base_offset
        gun_base_z = player['pos'][2] + dir_z * gun_base_offset

        # Gun tip world position
        tip_world_x = gun_base_x + dir_x * gun_length
        tip_world_y = gun_y
        tip_world_z = gun_base_z + dir_z * gun_length

        # Direction vector
        direction = normalize_vector([dir_x, 0, dir_z])

        create_bullet([tip_world_x, tip_world_y, tip_world_z], direction, 'PLAYER', 1)
        # No brief post-fire alignment in TP (aim assist disabled)
        mouse_buttons[GLUT_LEFT_BUTTON] = "PROCESSED"

    if key==b'\x1b': 
        glutLeaveMainLoop()
    if k==b'v': 
        # Sync camera rotation when switching modes
        global tp_camera_yaw_offset
        if camera_mode == CAMERA_MODE_FIRST_PERSON:
            # Switching to third-person: sync tp_camera_yaw_offset with player rotation
            tp_camera_yaw_offset = player['rotation_y']
        else:
            # Switching to first-person: sync player rotation with tp_camera_yaw_offset
            player['rotation_y'] = tp_camera_yaw_offset
        camera_mode = 1-camera_mode # Toggle 0 and 1
    if k==b'h' and player['health_perk_available']: 
        player['health']=PLAYER_MAX_HEALTH
        player['health_perk_available']=False
        player['kills_for_health_perk']=0
        pass  # Health Perk activated
    if k==b'f' and player['score_perk_available']:
        player['score_perk_time_left']=PERK_SCORE_MULTIPLIER_DURATION
        player['score_perk_available']=False
        player['kills_for_score_perk']=0
        pass  # Score Perk activated
    if k==b'g' and player['gun_perk_available']: 
        player['gun_perk_time_left']=PERK_RAPID_FIRE_DURATION
        player['gun_perk_available']=False
        player['kills_for_gun_perk']=0
        pass  # Gun Perk activated

def keyboard_up(key,x,y): 
    keys_pressed[key.lower()]=False
def special_keys_input(key,x,y): 
    special_keys_pressed[key]=True
def special_keys_up(key,x,y): 
    special_keys_pressed[key]=False
def mouse_click(button,state,x,y): 
    """Mouse input: UI clicks in menus/pause/win; fire during gameplay on left-click."""
    global mouse_buttons, game_state, win_score_recorded, mouse_pos
    mouse_buttons[button]=state # Store exact state
    # Convert y to UI space (GLUT gives y from top-left? Here we used ortho with origin bottom-left)
    ui_y = SCREEN_HEIGHT - y
    mouse_pos['x'], mouse_pos['y'] = x, ui_y
    # Handle UI clicks in menu/pause states
    if state==GLUT_DOWN and button==GLUT_LEFT_BUTTON:
        if game_state in (STATE_MAIN_MENU, STATE_LEVEL_SELECT, STATE_HALL_OF_FAME, STATE_PAUSED, STATE_YOU_WIN):
            for rect in ui_buttons:
                if point_in_rect(x, ui_y, rect):
                    action = rect['action']
                    if action=='menu_start':
                        player['score'] = 0
                        player['health'] = PLAYER_MAX_HEALTH
                        init_level(1)
                        game_state = STATE_PLAYING
                        return
                    if action=='menu_select_level':
                        game_state = STATE_LEVEL_SELECT
                        return
                    if action=='menu_hof':
                        game_state = STATE_HALL_OF_FAME
                        return
                    if action=='menu_exit':
                        # If player has a score not yet recorded, save it before exiting
                        if player.get('score', 0) > 0 and not current_session_score_recorded:
                            record_high_score(player['score'])
                        glutLeaveMainLoop()
                        return
                    if action=='back_to_main':
                        game_state = STATE_MAIN_MENU
                        return
                    if action.startswith('level_'):
                        try:
                            lvl = int(action.split('_')[1])
                            player['score'] = 0
                            player['health'] = PLAYER_MAX_HEALTH
                            init_level(lvl)
                            game_state = STATE_PLAYING
                        except:
                            pass
                        return
                    if action=='pause_resume':
                        game_state = STATE_PLAYING
                        return
                    if action=='pause_retry':
                        player['score'] = 0
                        player['health'] = PLAYER_MAX_HEALTH
                        init_level(current_level)
                        game_state = STATE_PLAYING
                        return
                    if action=='pause_to_main':
                        # Record mid-run score when returning to main menu from pause
                        if player.get('score', 0) > 0 and not current_session_score_recorded:
                            record_high_score(player['score'])
                        game_state = STATE_MAIN_MENU
                        return
                    if action=='win_to_main':
                        # Already recorded on win; just go to main menu
                        game_state = STATE_MAIN_MENU
                        return
                    if action=='win_exit':
                        # Safe exit from win screen
                        if player.get('score', 0) > 0 and not current_session_score_recorded:
                            record_high_score(player['score'])
                        glutLeaveMainLoop()
                        return
    # Fire on left mouse button down if cooldown allows (only during gameplay)
    if button==GLUT_LEFT_BUTTON and state==GLUT_DOWN and game_state==STATE_PLAYING and player['shoot_cooldown']<=0:
        player['shoot_cooldown'] = player['current_shoot_cooldown_time']

        yaw_rad = math.radians(player['rotation_y'])

        gun_base_offset = 0.35 * PLAYER_TOTAL_HEIGHT
        gun_length = PLAYER_GUN_LENGTH
        shoulder_height = PLAYER_LEG_LENGTH + PLAYER_TORSO_HEIGHT * 0.8
        gun_y = player['pos'][1] - PLAYER_BODY_Y_OFFSET + shoulder_height

        dir_x = math.sin(yaw_rad)
        dir_z = math.cos(yaw_rad)

        gun_base_x = player['pos'][0] + dir_x * gun_base_offset
        gun_base_z = player['pos'][2] + dir_z * gun_base_offset

        tip_world_x = gun_base_x + dir_x * gun_length
        tip_world_y = gun_y
        tip_world_z = gun_base_z + dir_z * gun_length

        direction = normalize_vector([dir_x, 0, dir_z])

        create_bullet([tip_world_x, tip_world_y, tip_world_z], direction, 'PLAYER', 1)
    
def idle():
    """Idle callback: compute delta time and run updates for active states, then request redraw."""
    global last_time
    current_t=glutGet(GLUT_ELAPSED_TIME)/1000.0
    delta_t=current_t-last_time
    last_time=current_t
    if delta_t > 0.1: 
        delta_t=0.1
    if delta_t <= 0: 
        delta_t=1/60.0
    # Only advance gameplay when playing or in transitions; paused/menu states skip update
    if game_state in (STATE_PLAYING, STATE_LEVEL_TRANSITION, STATE_GAME_OVER_TRANSITION):
        update_game_state(delta_t)
    # update hover position to keep hover effect responsive (no-op; position set on mouse move/click)
    glutPostRedisplay()

def main():
    global last_time,glu_quadric
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(SCREEN_WIDTH,SCREEN_HEIGHT)
    glutCreateWindow(b"8bit Doom")
    glEnable(GL_DEPTH_TEST)
    # Smooth shading is within OpenGL fixed-function; retain for model visuals
    glShadeModel(GL_SMOOTH)
    glClearColor(0.05,0.05,0.15,1.0)
    glu_quadric=gluNewQuadric()
    init_level_configs()
    init_player()
    # Start on main menu; do not init level here
    last_time=glutGet(GLUT_ELAPSED_TIME)/1000.0
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_keys_input)
    glutSpecialUpFunc(special_keys_up)
    glutMouseFunc(mouse_click)
    glutIdleFunc(idle)
    # Game Controls: W/A/S/D:Move | Q,E:Rotate | LeftClick/Space:Shoot | Arrows:Cam | F:View | H,C,G:Perks | ESC:Exit
    glutMainLoop()

if __name__ == "__main__": main()
