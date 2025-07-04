from flask import Flask, render_template, redirect, url_for, session, request
from flask_session import Session
from datetime import timedelta
import os
import torch
import random
import re
from poker_monster import (
    Network, create_action, GameState, Player, build_decks, 
    hyperparameters, num_actions, 
    PHASE_AWAITING_INPUT, PHASE_PLAYING_SELECTED_CARD, PHASE_VIEWING_CARD_INFO,
    PHASE_SELECTING_GRAVEYARD_CARD, PHASE_REORDERING_DECK_TOP3, PHASE_DISCARDING_CARD_FROM_OPP_HAND,
    PHASE_CHOOSING_GO_ALL_IN_TARGET, PHASE_CHOOSING_FOLD_TARGET, PHASE_CHOOSING_POKER_FACE_TARGET,
    PHASE_CHOOSING_CHEAP_SHOT_TARGET, PHASE_CHOOSING_ULTIMATUM_CARD, PHASE_OPP_CHOOSING_FROM_ULTIMATUM,
    PHASE_CHOOSING_FROM_DECK_TOP2, PHASE_HAND_FULL_DISCARDING_CARD,
    ERROR_ENEMY_HAS_THE_SUN, ERROR_ENEMY_HAS_THE_MOON, ERROR_INVALID_SELECTION,
    ERROR_CANT_PLAY_ANOTHER_POWER_CARD, ERROR_NOT_ENOUGH_POWER, ERROR_NO_SACRIFICE,
    ERROR_MUST_PICK_DIFFERENT_CARD, ERROR_MUST_HAVE_DIFFERENT_NAME, ERROR_NO_FURTHER_MOVES,
    ERROR_COMPUTERS_CANT_DO, ERROR_ACTION_WITHELD_FROM_AI
)

app = Flask(__name__)
# A secret key is required to use sessions
app.secret_key = 'a_very_secret_key'

# This uses Flask Session to run the cookie on the server side (the gamestate + hidden state is too large for browser)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)
Session(app)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
hero_ai = Network(name="hero", **hyperparameters)
monster_ai = Network(name="monster", **hyperparameters)
hero_ai.to(device)
monster_ai.to(device)
try:  # Load hero_ai
    hero_ai.load("hero")
except Exception as e:
    print(f"Could not load hero_ai: {e}")
try:  # Load monster_ai
    monster_ai.load("monster")
except Exception as e:
    print(f"Could not load monster_ai: {e}")
hero_ai.temperature = 0.0001
monster_ai.temperature = 0.0001

def serialize_rnn_state(rnn_state):
    """Converts a PyTorch hidden state tuple into a serializable list tuple."""
    return rnn_state.tolist()

def deserialize_rnn_state(state_list):
    """Converts a list tuple from the session back into a PyTorch hidden state."""
    return torch.tensor(state_list).to(device)

def get_display_info(gs):
    """Packages all relevant GameState data into a dictionary for the template."""

    if gs.me.going_first:
        my_turn_number = gs.turn_number / 2 + 1
    else:
        my_turn_number = (gs.turn_number + 1) / 2
    
    # Base player information
    info = {
        "turn_number": int(my_turn_number),
        "turn_priority": gs.turn_priority,
        "game_phase": gs.game_phase,
        "me": {
            "name": gs.me.name, "health": gs.me.health, "power": gs.me.power,
            "deck_size": len(gs.me.deck),
            "hand": [c.to_dict() for c in gs.me.hand],
            "power_cards": [c.to_dict() for c in gs.me.power_cards],
            "battlefield": [c.to_dict() for c in gs.me.battlefield],
            "graveyard": [c.to_dict() for c in gs.me.graveyard]
        },
        "opp": {
            "name": gs.opp.name, "health": gs.opp.health, "power": gs.opp.power,
            "deck_size": len(gs.opp.deck),
            "hand_size": len(gs.opp.hand),
            "power_cards_size": len(gs.opp.power_cards),
            "battlefield": [c.to_dict() for c in gs.opp.battlefield],
            "graveyard": [c.to_dict() for c in gs.opp.graveyard],
            "last_turn_log": gs.opp.last_turn_log
        },
        "cache": [c.to_dict() for c in gs.cache],
        "special_info": None, # Placeholder for conditional information
    }

    # Special Info:
    # Noble Sacrifice discard
    if gs.game_phase == PHASE_DISCARDING_CARD_FROM_OPP_HAND:  
        info["special_info"] = f"Opp hand: {[card.name for card in gs.opp.hand]}"
    # Peek top2 reveal
    elif gs.game_phase == PHASE_CHOOSING_FROM_DECK_TOP2:
        top2 = gs.me.deck[:2]
        info["special_info"] = f"My deck top 2 cards: {[card.name for card in top2]}"
    # Ultimatum deck reveal
    elif gs.game_phase == PHASE_CHOOSING_ULTIMATUM_CARD:
        info["special_info"] = f"My deck: {[card.name for card in gs.me.deck]}"
    # Ultimatum ultimatum
    elif gs.game_phase == PHASE_OPP_CHOOSING_FROM_ULTIMATUM:
        info["special_info"] = f"Opp Ultimatum: {[card.name for card in gs.cache[1:3]]}"
    # Reconsider reveal
    elif gs.game_phase == PHASE_REORDERING_DECK_TOP3:
        top3 = gs.me.deck[:3]
        info["special_info"] = f"My deck top 3 cards: {[card.name for card in top3]}"
    # Viewing card info
    elif gs.game_phase == PHASE_VIEWING_CARD_INFO:
        info["special_info"] = f"{gs.cache[0].name}: {gs.cache[0].card_text} (Power Cost: {gs.cache[0].power_cost})"
    # To show who is going first
    elif my_turn_number == 1:
        info["special_info"] = "You are going first" if gs.me.going_first else "You are going second"

    return info

def get_available_actions(gs):
    actions = []

    def add_spaces(text):
        spaced_text = re.sub(r'(\B[A-Z])', r' \1', text)
        lower_text = spaced_text.lower()
        return lower_text.capitalize()

    for action_id in range(num_actions):  # Assuming 20 possible actions
        # print("Creating action: ", action_id)
        action = create_action(gs, action_id)
        legal, error = action.is_legal()

        if legal:
            extra_info = ""
            action_name = type(action).__name__  # Get the class name
            if action_name in "SelectFromHand":
                extra_info = f"- {action.resolving_card.name}" if action.card_list else ""
            if action_name == "SelectFromBattlefield":
                extra_info = f"- {action.target.name}" if action.card_list else ""
            if action_name == "SelectFromOwnBattlefield":
                extra_info = f"- {action.sacrifice.name}" if action.card_list else ""
            if action_name == "SelectFromOppHand":
                extra_info = f"- {action.discard.name}" if action.card_list else ""
            if action_name == "SelectFromDeckTop2":
                extra_info = f"- {action.selected_card.name}" if action.card_list else ""
            if action_name == "SelectFromGraveyard":
                extra_info = f"- {action.selected_card.name}" if action.card_list else ""
            if action_name == "SelectFromDeck":
                extra_info = f"- {action.selected_card.name}" if action.card_list else ""
            if action_name == "SelectFromUltimatum":
                extra_info = f"- {action.selected_card.name}" if action.card_list else ""
            if action_name == "SelectFromDeckTop3":
                extra_info = f"- {action.selected_card.name}" if action.card_list else ""
            total_string = add_spaces(action_name) + " " + extra_info
            actions.append({"id": action_id, "name": total_string})
        elif error != ERROR_INVALID_SELECTION:  # QOL, error invalid shows up too often and don't need to see it
            total_string = "(Invalid) - " + error
            actions.append({"id": action_id, "name": total_string})
    
    return actions

def take_ai_turn(gs, prev_rnn_state):
    """Processes the AI's turn, managing its hidden state."""
    # This loop handles cases where the AI might take multiple actions in a row
    while gs.winner is None and gs.me.player_type.startswith("computer"):
        if gs.me.player_type in ["computer_ai", "computer_mind_control"]:
            if gs.me.player_type == "computer_mind_control":
                print("Player is Mind Controlled")

            current_ai = hero_ai if gs.me.name == "hero" else monster_ai
            
            choice_number, new_rnn_state = current_ai.sample_action(gs, prev_rnn_state, training=False)
            prev_rnn_state = new_rnn_state # Use the new state for the next potential loop

            action = create_action(gs, choice_number)
            action.enact() # This function modifies gs in place

        elif gs.me.player_type == "computer_random":
            while True:
                choice_number = randint(0, num_actions - 2)
                action = create_action(gs, choice_number)
                legal, reason = action.enact()
                if legal:
                    break

    return gs, new_rnn_state

@app.route("/")
def choice_screen():
    # Pop the winner from the session if it exists, so it only shows once.
    static_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    backgrounds_path = os.path.join(static_folder_path, 'backgrounds')
    
    # Get a list of all image files in that folder
    try:
        background_images = [f for f in os.listdir(backgrounds_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
        # Choose one random image from the list
        random_background = random.choice(background_images) if background_images else None
    except FileNotFoundError:
        random_background = None
        print("Warning: 'static/backgrounds' folder not found.")
    
    winner = session.pop('winner', None)
    
    return render_template('index.html', winner=winner, background_image=random_background)

@app.route("/start_game")
def start_game():
    """Initializes a new game based on the user's role choice."""
    user_role = request.args.get("role")
    difficulty = int(request.args.get("difficulty", 0)) 

    hero_mcontrol, monster_mcontrol = False, False
    if user_role == "hero":
        hero_player_type, monster_player_type = "person", "computer_ai"
        if difficulty in [1, 2]:  # Shuffle Mind Control into enemy deck for higher difficulty
            hero_mcontrol, monster_mcontrol = False, True
            print("Shuffled in Mind Control")
    elif user_role == "monster":
        hero_player_type, monster_player_type = "computer_ai", "person"
        if difficulty in [1, 2]:
            hero_mcontrol, monster_mcontrol = True, False
            print("Shuffled in Mind Control")
    else:
        return redirect(url_for("choice_screen"))
    
    hero_deck, monster_deck = build_decks(hero_mcontrol, monster_mcontrol)
    hero = Player("hero", hero_deck, hero_player_type)
    monster = Player("monster", monster_deck, monster_player_type)

    # Difficulty adjustment: add power savings for Hard mode
    monster.game_mode = 0
    hero.game_mode = 0
    if difficulty == 2:
        if user_role == "hero":
            monster.game_mode = 1
        else:
            hero.game_mode = 1
    
    going_first = "hero" if random.randint(0, 1) == 1 else "monster"
    if going_first == "hero":
        hero.going_first = True
    else:
        monster.going_first = True
    
    gs = GameState(hero, monster, going_first, PHASE_AWAITING_INPUT, cache=[])
    gs.hero.shuffle()
    gs.monster.shuffle()
    gs.hero.draw(4)
    gs.monster.draw(4)

    # Initialize a blank hidden state for the AIs
    h0 = torch.zeros(hyperparameters["num_rnn_layers"], hyperparameters["rnn_size"])
    rnn_state = h0

    # If the AI goes first, let it take its turn now
    if gs.me.player_type.startswith("computer_ai"):
        gs, rnn_state = take_ai_turn(gs, rnn_state)

    # Store the initial game and AI states in the session
    session["gs"] = gs.to_dict()
    session["rnn_state"] = serialize_rnn_state(rnn_state)
    
    return redirect(url_for("game"))

@app.route("/game")
def game():
    if "gs" not in session:
        return redirect(url_for("choice_screen"))

    gs = GameState.from_dict(session["gs"])

    if gs.winner:
        session['winner'] = gs.winner
        return redirect(url_for("choice_screen"))

    player_role_class = ""
    if gs.hero.player_type == 'person':
        player_role_class = 'player-is-hero'
    elif gs.monster.player_type == 'person':
        player_role_class = 'player-is-monster'
    
    # Get the necessary info to display
    game_info = get_display_info(gs)
    available_actions = get_available_actions(gs)
    
    return render_template("game.html", info=game_info, actions=available_actions, player_role=player_role_class)

@app.route("/submit_action", methods=["POST"])
def submit_action():
    if "gs" not in session:
        return redirect(url_for("choice_screen"))
    
    # Load state from session
    gs = GameState.from_dict(session["gs"])
    rnn_state = deserialize_rnn_state(session.get("rnn_state"))

    # Get action_id from the form submission
    action_id = int(request.form["action_id"])
    print(f"Action ID chosen: {action_id}")

    # Execute the user's action
    action = create_action(gs, action_id)
    legal, reason = action.is_legal()
    action.enact() # This updates gs

    # If the game isn't over, let the AI take its turn
    if gs.winner is None and gs.me.player_type.startswith("computer_ai"):
        gs, rnn_state = take_ai_turn(gs, rnn_state)
    print(gs.opp.last_turn_log)

    if gs.winner:
        # If there's a winner, store it in the session and redirect to the main page
        session["winner"] = gs.winner
        return redirect(url_for("choice_screen"))
    else:
        # If no winner, save the updated state and redirect back to the game board
        session["gs"] = gs.to_dict()
        session["rnn_state"] = serialize_rnn_state(rnn_state)
        return redirect(url_for("game"))

if __name__ == "__main__":
    app.run(debug=True)