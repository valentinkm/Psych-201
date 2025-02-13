import pandas as pd
import jsonlines
import random
import os


# Randomize the names of choice options
def randomized_choice_options(num_choices=5):
        names = ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]
        random.shuffle(names)
        return names

# Load armed bandit data
file1 = "armed_bandit_2023-04-28_out.csv"
file2 = "armed_bandit_2023-06-02_out.csv"

df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

df_all = pd.concat([df1, df2], ignore_index=True)

# Group the data by participant code and session code
# (Each group corresponds to one experimental session)
groups = df_all.groupby(["participant.code", "session.code"])

# Fixed instructions text for the multi-armed bandit task
instructions = (
        "MULTI‑ARMED BANDIT TASK\n\n"
        "Instructions:\n"
        "In this task, five buttons will be displayed on the screen. On each trial you must select one of these buttons by clicking on it. "
        "Each button is associated with a different average payout. You will first complete a practice block of 20 trials, followed by 4 incentivized blocks of 40 trials each.\n"
        "After every click the system takes about one second to process your entry. Within a given block, the average payout for each button remains constant—but between blocks the averages may change.\n\n"
        "Earnings:\n"
        "At the end of each block you will receive feedback on how many points you earned. Note that the practice block is not scored; only points from the 4 incentivized blocks determine your bonus payment (1 pence per 100 points earned)."
)

all_prompts = []

# Process each experimental session
for (participant_code, session_code), df_session in groups:
        # Sort trials by block and then by trial number
        df_session = df_session.sort_values(by=["block", "trial"])
        
        # Randomize the button names for this session
        choice_options = randomized_choice_options(num_choices=5)
        
        # Start building the prompt text
        prompt_text = instructions + "\n"
        prompt_text += "---\n"
        
        # Collect reaction times (if available)
        rt_list = []
        
        # Get the unique block numbers (e.g., 1 = practice, 2+ = incentivized)
        blocks = sorted(df_session["block"].unique())
        
        for block in blocks:
                # Select data for this block and compute cumulative points
                df_block = df_session[df_session["block"] == block]
                cumulative_points = df_block["player.payoff.1"].cumsum().tolist()
                
                # Label block: Block 1 is practice; subsequent blocks are incentivized (numbered block-1)
                if block == 1:
                        prompt_text += "Practice Block:\n\n"
                else:
                        prompt_text += f"Incentivized Block {block - 1}:\n\n"
                
                # Iterate over trials in the block
                for i, (_, row) in enumerate(df_block.iterrows()):
                        trial_num = int(row["trial"])
                        points = int(row["player.payoff.1"])
                        cumulative = int(cumulative_points[i])
                        # Use the participant's selection (assumed 1-indexed) to index into randomized buttons
                        selection = int(row["player.selection"])
                        try:
                                chosen_button = choice_options[selection - 1]
                        except IndexError:
                                chosen_button = f"Option{selection}"
                        
                        # Record reaction time if available
                        if "player.submission_times" in row and pd.notnull(row["player.submission_times"]):
                                        rt_list.append(row["player.submission_times"])
                        
                        trial_line = (f"Trial {trial_num}: Displayed buttons: {choice_options}. "
                                                    f"You selected <<{chosen_button}>> and received {points} points. "
                                                    f"Total points: {cumulative}.\n")
                        prompt_text += trial_line
                prompt_text += "\n"
        
        prompt_text += "---\n"
        prompt_text += "End of session.\n"
        
        # Prompt dict for one session
        prompt_dict = {
                "text": prompt_text,
                "experiment": "multi_armed_bandit",
                "participant": participant_code,
                "session": session_code,
                "RTs": rt_list
        }
        
        all_prompts.append(prompt_dict)

# Write all to jsonl
script_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(script_dir, "prompts.jsonl")
with jsonlines.open(output_file, mode='w') as writer:
        writer.write_all(all_prompts)

print(f"Created {len(all_prompts)} prompt(s) in {output_file}.")
