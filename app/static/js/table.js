const tableFactory = (tableId, tableData, columns,  tableSettings = {}, columnsSettings = [] ) =>{
        
    const rowHighlightColor = "#c4ffdb"
    const dataKeys = Object.keys(tableData[0]);
    const dynamicTableId = tableId
    let selectedRow = {[dynamicTableId]:tableId}
    let prevSelectedRow = {[dynamicTableId]:-1}

    const container = document.getElementById(tableId);

    const hyperformulaInstance = HyperFormula.buildEmpty({
        licenseKey: 'internal-use-in-handsontable',
    });

    let currSettings = {
        
        data: tableData,
        colHeaders: columns,
        filters: true,
        dropdownMenu: true, 
        readOnly: true,
        formulas: true,
        contextMenu: true,
        enterMoves: {row: 0, col: 0},
        renderAllRows: false,
        stretchH: 'all',
        className: "htCenter",  
        columnSorting: true,      
        columnSorting: {
            indicator: true,
            sortEmptyCells: true,
            initialConfig: {
              column: 0,
              sortOrder: 'desc'
            }
        },  
        fillHandle: true,    
        formulas: {
            engine: hyperformulaInstance,
            sheetName: 'Sheet1'
        },
        licenseKey: 'non-commercial-and-evaluation',
        
        beforeSetRangeStart: function(coordinates){            
            selectedRow[dynamicTableId] = hot.getDataAtRow(coordinates.row) 
            if(prevSelectedRow[dynamicTableId] !== -1){
                for (let j = 0; j < hot.countCols(); j++) {                    
                    const innerCell = hot.getCell(prevSelectedRow[dynamicTableId],j);
                    // console.log('DEB', innerCell)
                    try {                        
                        innerCell.style.background = "#fff"
                    } catch (error) {
                        console.log(error);
                    }
                }
            }
            // console.log('seeeeelcted ---> ',selectedRow[dynamicTableId], coordinates,prevSelectedRow);
            prevSelectedRow[dynamicTableId] = coordinates.row

        }, 
        afterSelectionEnd: function(r, c){

            // console.log('in afterSelectionEnd')
            for (var i = 0; i < hot.countCols(); i++) {
                try{
                    var cell = hot.getCell(r,i); 
                    cell.style.background = rowHighlightColor;                                       
                    cell.style.color = 'black';

                }catch(e){
                    // console.log(e);
                }
            }             
        }                                        
    }    
    
    Object.keys(tableSettings).forEach((s) =>{
        try{
            currSettings[s] = tableSettings[s]
        }catch(e){}        
    })
    if(columnsSettings.length > 0){
        console.log('columnsSettings',columnsSettings)
        currSettings['columns'] = dataKeys.map((x,i) => {
            const innerContainer = {}
            innerContainer.data = x;
            // console.log(columnsSettings[i]);
            try{
                Object.keys(columnsSettings[i]).forEach((y) => {
                    innerContainer[y] = columnsSettings[i][y]
                })
            }
            catch(e){
                console.log(e);
            }
            
            return innerContainer;
        })
        
    }


    const hot = new Handsontable(container,currSettings );
    
    hot.updateSettings(currSettings)
    

    clearLicenseInfo()
    return hot

}



