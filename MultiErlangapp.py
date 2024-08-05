import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyworkforce.queuing import MultiErlangC

def main():
    # Set up the page configuration
    st.set_page_config(page_title="Staffing Calculator", layout="wide")

    # Update the title
    st.title("Staffing Calculator Multiple Scenario Tester")

    # Adding a new section in the sidebar to indicate the creator
    st.sidebar.markdown("### Made by Ashwin Nair")

    # Collapsible sidebar for sensitivity parameters
    with st.sidebar.expander("User Inputs", expanded=False):
        acceptable_waiting_times = st.text_input("Acceptable Waiting Time (seconds, comma-separated)", "10,20,30").split(',')
        acceptable_waiting_times = [float(awt) for awt in acceptable_waiting_times if awt.strip().replace('.', '', 1).isdigit()]
        
        shrinkages = st.text_input("Shrinkage (% , comma-separated)", "20,30,40").split(',')
        shrinkages = [float(shrink) for shrink in shrinkages if shrink.strip().replace('.', '', 1).isdigit()]
        
        max_occupancies = st.text_input("Max Occupancy (% , comma-separated)", "70,80,90").split(',')
        max_occupancies = [float(occ) for occ in max_occupancies if occ.strip().replace('.', '', 1).isdigit()]

        service_level_targets = st.text_input("Service Level Targets (% , comma-separated)", "80,85,90").split(',')
        service_level_targets = [float(target) for target in service_level_targets if target.strip().replace('.', '', 1).isdigit()]

        working_hours = st.number_input("Working Hours per Day", min_value=1.0, max_value=24.0, value=8.0, step=0.5)
        working_days = st.number_input("Working Days per Week", min_value=1.0, max_value=7.0, value=5.0, step=0.5)

        # Option to choose AHT input method
        aht_input_option = st.radio(
            "Choose AHT (Average Handling Time) Input Method:",
            ("Multiple AHT values for all intervals and days", "AHT table at interval level for each day")
        )

        if aht_input_option == "Multiple AHT values for all intervals and days":
            average_handling_times = st.text_input("Average Handling Times (seconds, comma-separated)", "300,400,500").split(',')
            average_handling_times = [float(aht) for aht in average_handling_times if aht.strip().replace('.', '', 1).isdigit()]
        else:
            average_handling_times = []

    # User Guide in the Sidebar
    with st.sidebar.expander("📘 How to Use the App", expanded=False):
        st.markdown("""
        ## Welcome to the Staffing Calculator!
        This tool is designed to help you determine staffing requirements for call centers based on various scenarios. Here’s a step-by-step guide on how to use the app effectively:

        ### Step 1: Enter User Inputs
        - **Acceptable Waiting Time:** Input acceptable waiting times in seconds, separated by commas. E.g., `10,20,30`.
        - **Shrinkage:** Enter shrinkage percentages separated by commas. E.g., `20,30,40`.
        - **Max Occupancy:** Provide maximum occupancy percentages separated by commas. E.g., `70,80,90`.
        - **Service Level Targets:** Set service level targets as percentages separated by commas. E.g., `80,85,90`.
        - **Working Hours per Day:** Specify the number of working hours per day.
        - **Working Days per Week:** Specify the number of working days per week.

        ### Step 2: Choose AHT Input Method
        - Select **"Multiple AHT values for all intervals and days"** if you wish to input AHT for all intervals and days at once.
        - Select **"AHT table at interval level for each day"** if you prefer to input AHT data per interval for each day individually.

        ### Step 3: Input Calls and AHT Data
        - **Calls Offered:** Enter the number of calls offered for each 30-minute interval from Sunday to Saturday.
        - **Average Handling Time (AHT):** If you chose the AHT table method, input AHT for each 30-minute interval for each day.

        ### Step 4: Calculate Staffing Requirements
        - Press the **"Calculate Staffing Requirements"** button to begin the calculation process. The app will compute staffing needs based on the inputs provided.

        ### Step 5: Analyze the Results
        - View detailed staffing requirements and total staffing needs displayed in tables.
        - Explore interactive heatmaps and bar charts to visualize staffing levels across different days and intervals.

        ### Tips:
        - Make sure to input realistic values for waiting times, shrinkage, and occupancy to get accurate staffing calculations.
        - Use the graphs and tables to identify trends and optimize your call center's efficiency.

        Feel free to experiment with different scenarios and adjust inputs to see how they affect staffing requirements. If you have any questions or feedback, please contact [Ashwin Nair](mailto:your-email@example.com).
        """)

    # Input field for calls per interval for the whole week
    st.header("Calls Offered per 30-minute Interval (Sunday to Saturday)")
    intervals = pd.date_range("00:00", "23:30", freq="30min").time
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    data_calls = {day: [0.0] * len(intervals) for day in days}
    calls_df = pd.DataFrame(data_calls, index=intervals)

    if "calls_df" not in st.session_state:
        st.session_state["calls_df"] = calls_df
    st.session_state["calls_df"] = st.data_editor(st.session_state["calls_df"], key="calls_df_editor")

    # Input field for AHT per interval for the whole week if table method is selected
    if aht_input_option == "AHT table at interval level for each day":
        st.header("Average Handling Time (AHT) per 30-minute Interval (Sunday to Saturday)")
        data_aht = {day: [0.0] * len(intervals) for day in days}
        aht_df = pd.DataFrame(data_aht, index=intervals)
        
        if "aht_df" not in st.session_state:
            st.session_state["aht_df"] = aht_df
        st.session_state["aht_df"] = st.data_editor(st.session_state["aht_df"], key="aht_df_editor")
        aht_df = st.session_state["aht_df"]

    # Button to calculate staffing requirements
    if st.button("Calculate Staffing Requirements"):
        progress_bar = st.progress(0)
        total_combinations = (len(acceptable_waiting_times) * len(shrinkages) * len(max_occupancies) * len(service_level_targets) * len(days) * len(intervals))
        current_progress = 0

        for awt in acceptable_waiting_times:
            for shrinkage in shrinkages:
                for max_occupancy in max_occupancies:
                    if aht_input_option == "Multiple AHT values for all intervals and days":
                        for avg_aht in average_handling_times:
                            for target in service_level_targets:
                                staffing_results = []
                                for day in days:
                                    for interval, calls in zip(intervals, st.session_state["calls_df"][day]):
                                        if calls == 0:
                                            continue  # Skip intervals with no calls

                                        param_grid = {"transactions": [calls], "aht": [avg_aht / 60], "interval": [30], "asa": [awt / 60], "shrinkage": [shrinkage / 100]}
                                        multi_erlang = MultiErlangC(param_grid=param_grid, n_jobs=-1)

                                        required_positions_scenarios = {"service_level": [target / 100], "max_occupancy": [max_occupancy / 100]}

                                        positions_requirements = multi_erlang.required_positions(required_positions_scenarios)

                                        for requirement in positions_requirements:
                                            requirement.update({
                                                "Day": day,
                                                "Interval": interval,
                                                "AWT": awt,
                                                "Shrinkage": shrinkage,
                                                "Max Occupancy": max_occupancy,
                                                "Average AHT": avg_aht,
                                                "Service Level Target": target,
                                                "raw_positions": requirement.get("raw_positions", 0),
                                                "positions": requirement.get("positions", 0),
                                                "service_level": requirement.get("service_level", 0),
                                                "occupancy": requirement.get("occupancy", 0),
                                                "waiting_probability": requirement.get("waiting_probability", 0)
                                            })
                                            staffing_results.append(requirement)

                                        current_progress += 1
                                        progress_bar.progress(min(current_progress / total_combinations, 1.0))

                                staffing_df = pd.DataFrame(staffing_results)
                                
                                # Check for missing columns and add them if needed
                                required_columns = [
                                    "Day", "Interval", "AWT", "Shrinkage", "Max Occupancy",
                                    "Average AHT", "Service Level Target", "raw_positions", "positions",
                                    "service_level", "occupancy", "waiting_probability"
                                ]

                                # Adding missing columns with default values
                                for column in required_columns:
                                    if column not in staffing_df.columns:
                                        staffing_df[column] = 0

                                # Filter only the required columns
                                staffing_df = staffing_df[required_columns]

                                st.write(f"Staffing Requirements for AWT: {awt}s, Shrinkage: {shrinkage}%, Max Occupancy: {max_occupancy}%, Average AHT: {avg_aht}s, Service Level Target: {target}%")
                                st.dataframe(staffing_df)

                                total_staffing = staffing_df.groupby("Day")[["raw_positions", "positions"]].sum()
                                total_staffing["Sum of Raw Positions"] = total_staffing["raw_positions"]
                                total_staffing["Sum of Positions"] = total_staffing["positions"]
                                total_staffing["Divided by 2"] = total_staffing["Sum of Positions"] / 2
                                total_staffing["Divided by Working Hours"] = total_staffing["Divided by 2"] / working_hours
                                total_staffing["Maximum Value"] = total_staffing["Divided by Working Hours"].max()
                                total_staffing["Sum of the Week"] = total_staffing["Divided by Working Hours"].sum()
                                total_staffing["Divided by Working Days"] = total_staffing["Sum of the Week"] / working_days

                                # Ensure the table is sorted from Sunday to Saturday
                                total_staffing = total_staffing.reindex(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                                
                                st.write("Total Staffing")
                                st.dataframe(total_staffing)

                                # Interactive Heatmap
                                st.write("Interactive Heatmap of Staffing Levels")
                                heatmap_data = staffing_df.pivot_table(index="Day", columns="Interval", values="positions", aggfunc="mean")
                                heatmap_data = heatmap_data.reindex(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                                fig = go.Figure(data=go.Heatmap(
                                    z=heatmap_data.values,
                                    x=heatmap_data.columns,
                                    y=heatmap_data.index,
                                    colorscale='YlGnBu'
                                ))
                                fig.update_layout(
                                    title=f'Staffing Levels Heatmap (AWT: {awt}s, Shrinkage: {shrinkage}%, Max Occupancy: {max_occupancy}%, Average AHT: {avg_aht}s, Service Level Target: {target}%)',
                                    xaxis_nticks=48
                                )
                                st.plotly_chart(fig)

                                # Interactive Plot in Expander
                                with st.expander(f"Interactive Plot of Staffing Levels for AWT: {awt}s, Shrinkage: {shrinkage}%, Max Occupancy: {max_occupancy}%, Average AHT: {avg_aht}s, Service Level Target: {target}%"):
                                    for day in days:
                                        daily_staffing = staffing_df[staffing_df["Day"] == day]
                                        fig = px.bar(daily_staffing, x="Interval", y="positions", title=f'Staffing Levels on {day} (Service Level Target: {target}%)')
                                        fig.update_xaxes(tickvals=[str(t) for t in intervals])
                                        st.plotly_chart(fig)

                    else:
                        for target in service_level_targets:
                            staffing_results = []
                            for day in days:
                                for interval, calls, aht in zip(intervals, st.session_state["calls_df"][day], aht_df[day]):
                                    if calls == 0 or aht == 0:
                                        continue  # Skip intervals with no calls or no AHT

                                    param_grid = {"transactions": [calls], "aht": [aht / 60], "interval": [30], "asa": [awt / 60], "shrinkage": [shrinkage / 100]}
                                    multi_erlang = MultiErlangC(param_grid=param_grid, n_jobs=-1)

                                    required_positions_scenarios = {"service_level": [target / 100], "max_occupancy": [max_occupancy / 100]}

                                    positions_requirements = multi_erlang.required_positions(required_positions_scenarios)

                                    for requirement in positions_requirements:
                                        requirement.update({
                                            "Day": day,
                                            "Interval": interval,
                                            "AWT": awt,
                                            "Shrinkage": shrinkage,
                                            "Max Occupancy": max_occupancy,
                                            "Average AHT": aht,
                                            "Service Level Target": target,
                                            "raw_positions": requirement.get("raw_positions", 0),
                                            "positions": requirement.get("positions", 0),
                                            "service_level": requirement.get("service_level", 0),
                                            "occupancy": requirement.get("occupancy", 0),
                                            "waiting_probability": requirement.get("waiting_probability", 0)
                                        })
                                        staffing_results.append(requirement)

                                    current_progress += 1
                                    progress_bar.progress(min(current_progress / total_combinations, 1.0))

                            staffing_df = pd.DataFrame(staffing_results)

                            # Check for missing columns and add them if needed
                            required_columns = [
                                "Day", "Interval", "AWT", "Shrinkage", "Max Occupancy",
                                "Average AHT", "Service Level Target", "raw_positions", "positions",
                                "service_level", "occupancy", "waiting_probability"
                            ]

                            # Adding missing columns with default values
                            for column in required_columns:
                                if column not in staffing_df.columns:
                                    staffing_df[column] = 0

                            # Filter only the required columns
                            staffing_df = staffing_df[required_columns]

                            st.write(f"Staffing Requirements for AWT: {awt}s, Shrinkage: {shrinkage}%, Max Occupancy: {max_occupancy}%, Average AHT: {aht}s, Service Level Target: {target}%")
                            st.dataframe(staffing_df)

                            total_staffing = staffing_df.groupby("Day")[["raw_positions", "positions"]].sum()
                            total_staffing["Sum of Raw Positions"] = total_staffing["raw_positions"]
                            total_staffing["Sum of Positions"] = total_staffing["positions"]
                            total_staffing["Divided by 2"] = total_staffing["Sum of Positions"] / 2
                            total_staffing["Divided by Working Hours"] = total_staffing["Divided by 2"] / working_hours
                            total_staffing["Maximum Value"] = total_staffing["Divided by Working Hours"].max()
                            total_staffing["Sum of the Week"] = total_staffing["Divided by Working Hours"].sum()
                            total_staffing["Divided by Working Days"] = total_staffing["Sum of the Week"] / working_days

                            # Ensure the table is sorted from Sunday to Saturday
                            total_staffing = total_staffing.reindex(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                            
                            st.write("Total Staffing")
                            st.dataframe(total_staffing)

                            # Interactive Heatmap
                            st.write("Interactive Heatmap of Staffing Levels")
                            heatmap_data = staffing_df.pivot_table(index="Day", columns="Interval", values="positions", aggfunc="mean")
                            heatmap_data = heatmap_data.reindex(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                            fig = go.Figure(data=go.Heatmap(
                                z=heatmap_data.values,
                                x=heatmap_data.columns,
                                y=heatmap_data.index,
                                colorscale='YlGnBu'
                            ))
                            fig.update_layout(
                                title=f'Staffing Levels Heatmap (AWT: {awt}s, Shrinkage: {shrinkage}%, Max Occupancy: {max_occupancy}%, Average AHT: {aht}s, Service Level Target: {target}%)',
                                xaxis_nticks=48
                            )
                            st.plotly_chart(fig)

                            # Interactive Plot in Expander
                            with st.expander(f"Interactive Plot of Staffing Levels for AWT: {awt}s, Shrinkage: {shrinkage}%, Max Occupancy: {max_occupancy}%, Average AHT: {aht}s, Service Level Target: {target}%"):
                                for day in days:
                                    daily_staffing = staffing_df[staffing_df["Day"] == day]
                                    fig = px.bar(daily_staffing, x="Interval", y="positions", title=f'Staffing Levels on {day} (Service Level Target: {target}%)')
                                    fig.update_xaxes(tickvals=[str(t) for t in intervals])
                                    st.plotly_chart(fig)

        progress_bar.empty()  # Remove the progress bar once the results are updated

if __name__ == "__main__":
    main()
