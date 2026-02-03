

def update_label_to_style_from_stackplot(label_to_style, legend_order, polycols, labels):
    # polycols is a list of PolyCollection, returned by stackplot
    for pc, lab in zip(polycols, labels):
        if lab not in label_to_style:
            # Take the facecolor used by this PolyCollection
            fc = pc.get_facecolor()
            color = tuple(fc[0]) if len(fc) else None
            label_to_style[lab] = {"color": color, "alpha": pc.get_alpha() or 1.0}
            legend_order.append(lab)


def batch_plot_stacked_volumes(ther, bulks, p_path, t_path, bulks_labels = None, members_set=None,
                               shrink=None, shrink_part=0.95, normalize=True, normalize_to_solids=False,
                               liq_phases=None,
                               move_end_lists=None, move_front_lists=None, verbose=0):
    idx = 0
    label_to_style = {}  # label -> dict(color=..., hatch=..., etc.)
    legend_order = []  # keep consistent ordering
    if not bulks_labels or len(bulks_labels) > len(bulks):
        bulks_labels = [f"bulk{i}" for i in range(len(bulks))]
    elif len(bulks_labels) < len(bulks):
        bulks_labels += [f"bulk{i}" for i in range(len(bulks_labels), len(bulks))]

    for bulk in bulks:
        if verbose:
            print("Bulk", idx, bulk)
        bulk_arr = [bulk] * len(p_path)
        states = ther.compute_pt_path(p_path, t_path, bulk_arr)
        if members_set:
            states.set_members(members_set)

        polycols, labels_in_plot = states.plot_path_stacked_volumes(t_path,
                                                                    title=bulks_labels[idx],
                                                                    shrink=shrink,
                                                                    normalize=normalize,
                                                                    normalize_to_solids=normalize_to_solids,
                                                                    liq_phases=liq_phases,
                                                                    shrink_part=shrink_part,
                                                                    label_to_style=label_to_style,
                                                                    move_end_lists=move_end_lists,
                                                                    move_front_lists=move_front_lists,
                                                                    return_polycols=True
                                                                    )

        # update global style registry with any new labels (using their actual plotted colors)
        update_label_to_style_from_stackplot(label_to_style, legend_order, polycols, labels_in_plot)

        idx += 1
