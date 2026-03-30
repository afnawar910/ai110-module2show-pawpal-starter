import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")


def _valid_time(value: str) -> bool:
    """Return True if value is a valid HH:MM string."""
    try:
        parts = value.split(":")
        return len(parts) == 2 and 0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59
    except (ValueError, AttributeError):
        return False

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None
if "setup_done" not in st.session_state:
    st.session_state.setup_done = False
if "schedule" not in st.session_state:
    st.session_state.schedule = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
st.caption("Your daily pet care planner")
st.divider()

# ---------------------------------------------------------------------------
# STEP 1 — Owner setup
# ---------------------------------------------------------------------------
if not st.session_state.setup_done:
    st.subheader("👤 Let's get started — tell us about yourself")
    with st.form("owner_form"):
        col1, col2 = st.columns(2)
        with col1:
            owner_name = st.text_input("Your name", placeholder="e.g. Jordan")
        with col2:
            available_time = st.slider("How many minutes do you have today?", 30, 480, 120, step=15)
        submitted = st.form_submit_button("Continue →", use_container_width=True)
        if submitted and owner_name.strip():
            st.session_state.owner = Owner(name=owner_name.strip(), available_time=available_time)
            st.session_state.setup_done = True
            st.rerun()
        elif submitted:
            st.warning("Please enter your name.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Sidebar — owner summary + reset
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 {owner.name}")
    st.metric("Time available today", f"{owner.available_time} min")
    st.divider()

    pets = owner.get_pets()
    if pets:
        st.markdown("**Your pets**")
        for pet in pets:
            task_count = len(pet.get_tasks())
            st.markdown(f"- **{pet.name}** ({pet.species}, {pet.age}y) — {task_count} task(s)")
    else:
        st.info("No pets added yet.")

    st.divider()
    if st.button("🔄 Start over", use_container_width=True):
        for key in ["owner", "setup_done", "schedule"]:
            del st.session_state[key]
        st.rerun()

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🐶 My Pets", "📋 Tasks", "📅 Daily Schedule"])

# ── TAB 1: Pets ─────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Add a pet")
    with st.form("pet_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            pet_name = st.text_input("Pet name", placeholder="e.g. Mochi")
        with c2:
            species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        with c3:
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
        add_pet = st.form_submit_button("➕ Add pet", use_container_width=True)
        if add_pet:
            if pet_name.strip():
                owner.add_pet(Pet(name=pet_name.strip(), species=species, age=age))
                st.success(f"{pet_name.strip()} added!")
                st.session_state.schedule = None
                st.rerun()
            else:
                st.warning("Please enter a pet name.")

    pets = owner.get_pets()
    if pets:
        st.divider()
        st.subheader("Your pets")
        cols = st.columns(min(len(pets), 3))
        for i, pet in enumerate(pets):
            with cols[i % 3]:
                st.markdown(f"### {pet.name}")
                st.write(f"**Species:** {pet.species.capitalize()}")
                st.write(f"**Age:** {pet.age} year(s)")
                tasks = pet.get_tasks()
                done  = sum(1 for t in tasks if t.is_completed)
                st.write(f"**Tasks:** {done}/{len(tasks)} completed")
                if st.button(f"Remove {pet.name}", key=f"remove_pet_{i}"):
                    owner.remove_pet(pet)
                    st.session_state.schedule = None
                    st.rerun()
    else:
        st.info("No pets yet — add one above to get started.")

# ── TAB 2: Tasks ────────────────────────────────────────────────────────────
with tab2:
    pets = owner.get_pets()
    if not pets:
        st.info("Add a pet first before adding tasks.")
    else:
        st.subheader("Add a task")
        with st.form("task_form"):
            c1, c2 = st.columns(2)
            with c1:
                selected_pet_name = st.selectbox("For which pet?", [p.name for p in pets])
                task_name  = st.text_input("Task name", placeholder="e.g. Morning walk")
                category   = st.selectbox("Category", ["walk", "feeding", "meds", "grooming", "enrichment", "other"])
                start_time = st.text_input("Start time (HH:MM, optional)", placeholder="e.g. 09:00")
            with c2:
                duration  = st.slider("Duration (minutes)", 5, 120, 20, step=5)
                priority  = st.radio("Priority", ["high", "medium", "low"], horizontal=True)
                frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])
            notes    = st.text_area("Notes (optional)", placeholder="Any extra details...")
            add_task = st.form_submit_button("➕ Add task", use_container_width=True)

            if add_task:
                if task_name.strip():
                    # Validate HH:MM format if provided
                    clean_time = start_time.strip()
                    if clean_time and not _valid_time(clean_time):
                        st.warning("Start time must be in HH:MM format (e.g. 09:00).")
                    else:
                        selected_pet = next(p for p in pets if p.name == selected_pet_name)
                        conflict_warning = selected_pet.add_task(Task(
                            name=task_name.strip(),
                            category=category,
                            duration=duration,
                            priority=priority,
                            frequency=frequency,
                            start_time=clean_time,
                            notes=notes.strip(),
                        ))
                        if conflict_warning:
                            st.warning(f"⚠️ Duplicate detected: {conflict_warning}")
                        else:
                            st.success(f"Task '{task_name.strip()}' added for {selected_pet_name}!")
                        st.session_state.schedule = None
                        st.rerun()
                else:
                    st.warning("Please enter a task name.")

        # --- Filter panel ---
        all_pairs = owner.get_all_tasks()
        if all_pairs:
            st.divider()
            st.subheader("All tasks")

            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                filter_pet = st.selectbox("Filter by pet", ["All"] + [p.name for p in pets], key="filter_pet")
            with fc2:
                filter_status = st.selectbox("Filter by status", ["All", "incomplete", "completed"], key="filter_status")
            with fc3:
                filter_cat = st.selectbox("Filter by category", ["All", "walk", "feeding", "meds", "grooming", "enrichment", "other"], key="filter_cat")

            scheduler = Scheduler(owner)
            filtered = scheduler.filter_tasks(
                pet_name = None if filter_pet    == "All" else filter_pet,
                status   = None if filter_status == "All" else filter_status,
                category = None if filter_cat    == "All" else filter_cat,
            )

            # Pre-flight conflict check on all tasks
            conflicts = scheduler.detect_conflicts(all_pairs)
            if conflicts:
                for w in conflicts:
                    st.error(f"⚠️ Schedule conflict: {w}")

            if not filtered:
                st.info("No tasks match the current filter.")
            else:
                # Group filtered results by pet
                pets_in_results = list({p.name: p for p, _ in filtered}.values())
                for pet in pets_in_results:
                    pet_tasks = [(p, t) for p, t in filtered if p.name == pet.name]
                    with st.expander(f"🐾 {pet.name} — {len(pet_tasks)} task(s)", expanded=True):
                        for idx, (_, task) in enumerate(pet_tasks):
                            c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 2, 2, 2, 1])
                            c1.write(f"**{task.name}**")
                            c2.write(f"{'✅' if task.is_completed else '⬜'}")
                            c3.write(f"⏱ {task.duration} min" + (f" @ {task.start_time}" if task.start_time else ""))
                            priority_badge = {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}
                            c4.write(priority_badge.get(task.priority, task.priority))
                            c5.write(f"🔁 {task.frequency}")
                            if c6.button("✕", key=f"del_{pet.name}_{idx}_{task.name}"):
                                pet.remove_task(task)
                                st.session_state.schedule = None
                                st.rerun()
                            if task.notes:
                                c1.caption(f"📝 {task.notes}")
        else:
            st.info("No tasks yet — add one above.")

# ── TAB 3: Schedule ─────────────────────────────────────────────────────────
with tab3:
    pets      = owner.get_pets()
    all_tasks = owner.get_all_tasks()

    if not pets:
        st.info("Add a pet and some tasks first.")
    elif not all_tasks:
        st.info("Add some tasks before generating a schedule.")
    else:
        total_tasks_time = sum(t.duration for _, t in all_tasks)
        c1, c2, c3 = st.columns(3)
        c1.metric("Pets", len(pets))
        c2.metric("Total tasks", len(all_tasks))
        c3.metric("Total task time", f"{total_tasks_time} min")

        st.divider()

        if st.button("✨ Generate my daily schedule", use_container_width=True, type="primary"):
            for _, task in all_tasks:
                task.mark_undone()
                task.is_urgent = False
            scheduler = Scheduler(owner)
            st.session_state.schedule = scheduler.generate()

        schedule = st.session_state.schedule
        if schedule:
            st.divider()
            scheduled = schedule.get_checklist()
            skipped   = schedule.get_skipped()
            conflicts = getattr(schedule, "_conflicts", [])

            # 1. Conflict warnings — most important, shown first
            if conflicts:
                st.error("⚠️ Time conflicts detected in your schedule:")
                for w in conflicts:
                    st.markdown(f"- {w}")
                st.caption("Tip: edit the start times of conflicting tasks in the Tasks tab to resolve this.")
                st.divider()

            # 2. Urgent reminder banner
            urgent = [(pet, task) for pet, task in scheduled if task.is_urgent]
            if urgent:
                st.warning("These high-priority tasks exceed your time budget — don't skip them!")
                for pet, task in urgent:
                    st.markdown(f"- **{task.name}** for {pet.name} ({task.duration} min)")
                st.divider()

            # 3. Time budget summary
            used  = schedule.total_time_used
            avail = owner.available_time
            col1, col2, col3 = st.columns(3)
            col1.metric("Scheduled", f"{used} min")
            col2.metric("Available", f"{avail} min")
            col3.metric("Remaining", f"{max(avail - used, 0)} min", delta=f"{avail - used} min")

            if used > avail:
                st.warning(f"You are {used - avail} min over budget — urgent high-priority tasks were kept.")
            else:
                st.success(f"Great! You have {avail - used} min to spare today.")

            st.divider()

            # 4. Interactive checklist (sorted by start_time via scheduler)
            st.subheader("✅ Today's checklist")
            for i, (pet, task) in enumerate(scheduled):
                col1, col2 = st.columns([7, 1])
                time_str   = f" @ {task.start_time}" if task.start_time else ""
                urgent_tag = " ⚠️" if task.is_urgent else ""
                label = f"**[{pet.name}]** {task.name}{time_str} — {task.duration} min · {task.priority}{urgent_tag}"
                checked = col1.checkbox(label, value=task.is_completed, key=f"chk_{i}_{pet.name}_{task.name}")
                if checked != task.is_completed:
                    if checked:
                        task.mark_done()
                    else:
                        task.mark_undone()
                if task.notes:
                    col1.caption(f"📝 {task.notes}")

            # Progress bar
            total  = len(scheduled)
            done   = sum(1 for _, t in scheduled if t.is_completed)
            if total > 0:
                st.divider()
                st.markdown(f"**Progress: {done}/{total} tasks completed**")
                st.progress(done / total)

            # 5. Skipped tasks
            if skipped:
                st.divider()
                with st.expander(f"⏭ Skipped tasks ({len(skipped)})"):
                    st.caption("These tasks were not scheduled today. Reasons are shown below.")
                    for pet, task, reason in skipped:
                        col1, col2 = st.columns([5, 3])
                        col1.markdown(f"**[{pet.name}]** {task.name} ({task.duration} min · {task.priority})")
                        col2.caption(reason)

            # 6. Full text summary
            st.divider()
            with st.expander("📋 Full schedule summary"):
                st.text(schedule.get_summary())


