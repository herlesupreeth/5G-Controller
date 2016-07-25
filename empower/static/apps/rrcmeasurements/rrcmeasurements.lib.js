
jQuery(document).ready(function($){

    var chartPriRSRP = c3.generate({
        bindto: '#priRSRPchart',
        data: {
            columns: [
                ['data', -140]
            ],
            type: 'gauge',
        },
        gauge: {
            label: {
                format: function(value, ratio) {
                    return "RSRP = " + value;
                },
                show: true
            },
            min: -140,
            max: -43,
            width: 25
            },
            color: {
                pattern: ['#FF0000', '#F97600', '#F6C600', '#60B044'],
                threshold: {
                    // Thresholds are based on good, bad, worst values of RSRP
                    values: [-100, -90, -80, -43]
                }
            },
            size: {
                height: 190
            }
        });

    var chartPriRSRQ = c3.generate({
        bindto: '#priRSRQchart',
        data: {
            columns: [
                ['data', -20]
            ],
            type: 'gauge',
        },
        gauge: {
            label: {
                format: function(value, ratio) {
                    return "RSRQ = " + value;
                },
                show: true
            },
            min: -20,
            max: -2,
            width: 25
            },
            color: {
                pattern: ['#FF0000', '#F97600', '#F6C600', '#60B044'],
                threshold: {
                    // Thresholds are based on good, bad, worst values of RSRQ
                    values: [-20, -15, -10, -2]
                }
            },
            size: {
                height: 190
            }
        });

        setTimeout(function () {
            chartPriRSRQ.load({
                columns: [['data', -19]]
            });
        }, 1000);
        
        loadVBSPsSelectBox(tenant_id);
        loadUEsSelectBox();
        
        // $('#vbspSelect').on('click', function(){
        //     loadUEsSelectBox();
        // });

        $('#UESelect').on('click', function(){
            loadMeasurements(chartPriRSRP, chartPriRSRQ);
        });

        var chartNeiRSRP = c3.generate({
            bindto: '#neighRSRPchart',
            data: {
                columns: [
                    ['data', -140]
                ],
                type: 'gauge',
            },
            gauge: {
                label: {
                    format: function(value, ratio) {
                        return "RSRP = " + value;
                    },
                    show: true
                },
                min: -141,
                max: -42,
                width: 25
                },
                color: {
                    pattern: ['#FF0000', '#F97600', '#F6C600', '#60B044'],
                    threshold: {
                        // Thresholds are based on good, bad, worst values of RSRP
                        values: [-100, -90, -80, -43]
                    }
                },
                size: {
                    height: 190
                }
            });

        var chartNeiRSRQ = c3.generate({
            bindto: '#neighRSRQchart',
            data: {
                columns: [
                    ['data', -20]
                ],
                type: 'gauge',
            },
            gauge: {
                label: {
                    format: function(value, ratio) {
                        return "RSRQ = " + value;
                    },
                    show: true
                },
                min: -21,
                max: -1,
                width: 25
                },
                color: {
                    pattern: ['#FF0000', '#F97600', '#F6C600', '#60B044'],
                    threshold: {
                        // Thresholds are based on good, bad, worst values of RSRQ
                        values: [-20, -15, -10, -2]
                    }
                },
                size: {
                    height: 190
                }
            });
});

function loadVBSPsSelectBox(tenant_id) {

    setTimeout(function() {
        $.getJSON("/api/v1/tenants/" + tenant_id + "/vbsps", function(data) {
            var selectVBSPMenu = $('#vbspSelect');
            var vbsp_values = [];
            $("#vbspSelect option").each(function(){
                vbsp_values.push($(this).val());
            });

            console.log("vbsps data" + data);
            // Check whether the selected vbsp still exists or not
            var selected_vbsp = $("#vbspSelect :selected").val();
            if (selected_vbsp !== ""){
                var vbsp_exist_flag = false;
                for (vbsp_index in data) {
                    if (selected_vbsp == data[vbsp_index].addr) {
                        vbsp_exist_flag = true;
                        break;
                    }
                }

                if (!vbsp_exist_flag){
                    $("#vbspSelect option").filter(function(index) {
                        return $(this).val() == selected_vbsp;
                    }).remove();
                    $('#UESelectMenuDiv').addClass("hidden");
                    $('#priCellMeas').addClass("hidden");
                    $('#neighCellsSelect').addClass("hidden");
                    $('#neighCellsMeas').addClass("hidden");
                    vbsp_values.splice(vbsp_values.indexOf(selected_vbsp),1);
                }
            }

            // Check if all the vbsp in the options still exist or not
            $.each(vbsp_values, function(index, value) {
                if (value !== ""){
                    var exist_flag = false;
                    for (vbsp_index in data) {
                        if (value == data[vbsp_index].addr) {
                            exist_flag = true;
                            data.splice(vbsp_index,1);
                            break;
                        }
                    }
                    if (!exist_flag){
                        $("#vbspSelect option").filter(function(index) {
                            return $(this).val() == value;
                        }).remove();
                    }
                }
            });

            $.each(data, function(index, vbsp) {
                selectVBSPMenu.append("<option value= "+ vbsp.addr +">" + vbsp.label + " (" + vbsp.addr + ")" + "</option>");
            });
            loadVBSPsSelectBox(tenant_id);
        });
    }, 3000);
}

function loadUEsSelectBox() {

    setTimeout(function() {
        var vbsp_id = $("#vbspSelect :selected").val();

        if (vbsp_id !== "") {
            var selectUEMenu = $('#UESelect');

            $.getJSON("/api/v1/vbsps/" + vbsp_id + "/ues", function(data) {

                console.log(data);
                if (data.length === 0) {
                    $('#UESelectMenuDiv').addClass("hidden");
                    $('#priCellMeas').addClass("hidden");
                    $('#neighCellsSelect').addClass("hidden");
                    $('#neighCellsMeas').addClass("hidden"); 
                } else {
                    $('#UESelectMenuDiv').removeClass("hidden");
                    var ue_values = [];
                    $("#UESelect option").each(function(){
                        ue_values.push($(this).val());
                    });

                    // Check whether the selected ue still exists or not
                    var selected_ue = $("#UESelect :selected").val();
                    if (selected_ue !== ""){
                        var ue_exist_flag = false;
                        for (ue_index in data) {
                            if (selected_ue == data[ue_index].rnti) {
                                ue_exist_flag = true;
                                break;
                            }
                        }

                        if (!ue_exist_flag){
                            $("#UESelect option").filter(function(index) {
                                return $(this).val() == selected_ue;
                            }).remove();
                            $('#priCellMeas').addClass("hidden");
                            $('#neighCellsSelect').addClass("hidden");
                            $('#neighCellsMeas').addClass("hidden");
                            ue_values.splice(ue_values.indexOf(selected_ue),1);
                        }
                    }

                    // Check if all the UEs in the options still exist or not
                    $.each(ue_values, function(index, value) {
                        if (value !== ""){
                            var exist_flag = false;
                            for (ue_index in data) {
                                if (value == data[ue_index].rnti) {
                                    exist_flag = true;
                                    data.splice(ue_index,1);
                                    break;
                                }
                            }
                            if (!exist_flag){
                                $("#UESelect option").filter(function(index) {
                                    return $(this).val() == value;
                                }).remove();
                            }
                        }
                    });

                    $.each(data, function(index, ue) {
                        selectUEMenu.append("<option value= "+ ue.rnti +">" + ue.rnti + "</option>");
                    });
                }
            });
        }
        loadUEsSelectBox();
    }, 3000);
}

function loadMeasurements(chartPriRSRP, chartPriRSRQ) {

    var vbsp_id_selected = $("#vbspSelect :selected").val();
    var ue_rnti_selected = $("#UESelect :selected").val();

    if (vbsp_id_selected !== "" && ue_rnti_selected !== "") {

        var selectCellIDMenu = $('#CellIDSelect');

        $('#priCellMeas').removeClass("hidden");
        
        setTimeout(function() {
            $.getJSON("/api/v1/tenants/" + tenant_id + "/vbsps/" + vbsp_id_selected + "/ues/" + ue_rnti_selected + "/ue_rrc_measurements", function(data) {

                // Loaad the primary cell measurements
                console.log("measurements data " + data);
                chartPriRSRP.load({
                    columns: [['data', data.primary_cell_rsrp]]
                });

                chartPriRSRQ.load({
                    columns: [['data', data.primary_cell_rsrq]]
                });

            loadMeasurements(chartPriRSRP, chartPriRSRQ);
            });
        }, 500);
    }    
}

function loadCellIDsSelectBox(measurements) {
    var selectVBSPMenu = $('#vbspSelect');
    var vbsp_values = [];
    $("#vbspSelect option").each(function(){
        vbsp_values.push($(this).val());
    });

    console.log("vbsps data" + data);
    // Check whether the selected vbsp still exists or not
    var selected_vbsp = $("#vbspSelect :selected").val();
    if (selected_vbsp !== ""){
        var vbsp_exist_flag = false;
        for (vbsp_index in data) {
            if (selected_vbsp == data[vbsp_index].addr) {
                vbsp_exist_flag = true;
                break;
            }
        }

        if (!vbsp_exist_flag){
            $("#vbspSelect option").filter(function(index) {
                return $(this).val() == selected_vbsp;
            }).remove();
            $('#UESelectMenuDiv').addClass("hidden");
            $('#priCellMeas').addClass("hidden");
            $('#neighCellsSelect').addClass("hidden");
            $('#neighCellsMeas').addClass("hidden");
            vbsp_values.splice(vbsp_values.indexOf(selected_vbsp),1);
        }
    }

    // Check if all the vbsp in the options still exist or not
    $.each(vbsp_values, function(index, value) {
        if (value !== ""){
            var exist_flag = false;
            for (vbsp_index in data) {
                if (value == data[vbsp_index].addr) {
                    exist_flag = true;
                    data.splice(vbsp_index,1);
                    break;
                }
            }
            if (!exist_flag){
                $("#vbspSelect option").filter(function(index) {
                    return $(this).val() == value;
                }).remove();
            }
        }
    });

    $.each(data, function(index, vbsp) {
        selectVBSPMenu.append("<option value= "+ vbsp.addr +">" + vbsp.label + " (" + vbsp.addr + ")" + "</option>");
    });
}