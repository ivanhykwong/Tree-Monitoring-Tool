# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GICTreeMonitoringTool
                                 A QGIS plugin
 This plugin serves as an intermediate step in the tree monitoring workflow developed by Geocarto International Centre Ltd.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-08-06
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Geocarto International Centre Ltd.
        email                : geocarto@geocarto.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QDialog, QInputDialog, QMessageBox, QTableWidgetItem, QWidget
from qgis.core import QgsProject, Qgis
from qgis.core import (QgsFields, QgsField, QgsFeature, QgsGeometry, QgsPointXY,
                       QgsFeatureRequest, QgsProject, QgsRaster, QgsRectangle, QgsRasterLayer,
                       QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes, 
                       QgsContrastEnhancement, QgsRasterMinMaxOrigin)
from qgis.core import (QgsProcessing, QgsFeatureSink, QgsProcessingException, QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink)
from qgis import processing

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .GIC_Tree_Monitoring_Tool_dialog import GICTreeMonitoringToolDialog
import os
import os.path
import csv
import numpy as np
import shutil
import random
import string


class GICTreeMonitoringTool:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GICTreeMonitoringTool_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GIC Tree Monitoring Tool')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GICTreeMonitoringTool', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/GIC_Tree_Monitoring_Tool/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'GIC Tree Monitoring Tool'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&GIC Tree Monitoring Tool'),
                action)
            self.iface.removeToolBarIcon(action)

    def select_output_file(self):
        filename, _filter = QFileDialog.getSaveFileName(self.dlg, "Select output file","", '*.txt')
        self.dlg.lineEdit.setText(filename)
    
    def set_input(self):
        # Clear the contents of the comboBox from previous runs
        self.dlg.comboBox_image1.clear()
        self.dlg.comboBox_image2.clear()
        self.dlg.comboBox_image3.clear()
        self.dlg.comboBox_image4.clear()
        self.dlg.comboBox_image5.clear()
        self.dlg.comboBox_point1.clear()
        self.dlg.comboBox_point2.clear()
        self.dlg.comboBox_point3.clear()
        self.dlg.comboBox_point4.clear()
        self.dlg.comboBox_point5.clear()
    
        # Fetch the currently loaded layers
        # layers = QgsProject.instance().layerTreeRoot().children()
        layer_list = []
        # layers = QgsProject.instance().mapLayers().values()
        for layer in QgsProject.instance().mapLayers().values():
            layer_list.append(layer)
    
        # Populate the comboBox with names of all the loaded layers
        raster_layer_list = []
        for layer in layer_list:
            if ( layer.type() == layer.RasterLayer ):
                raster_layer_list.append(layer)       
        point_layer_list = []
        for layer in layer_list:
            if ( layer.type() == layer.VectorLayer ) and ( layer.geometryType() == QgsWkbTypes.PointGeometry ):
                point_layer_list.append(layer)
        
        raster_layer_list_name = [""] + [layer.name() for layer in raster_layer_list]
        point_layer_list_name = [""] + [layer.name() for layer in point_layer_list]
        self.dlg.comboBox_image1.addItems(raster_layer_list_name)
        self.dlg.comboBox_image2.addItems(raster_layer_list_name)
        self.dlg.comboBox_image3.addItems(raster_layer_list_name)
        self.dlg.comboBox_image4.addItems(raster_layer_list_name)
        self.dlg.comboBox_image5.addItems(raster_layer_list_name)
        self.dlg.comboBox_point1.addItems(point_layer_list_name)
        self.dlg.comboBox_point2.addItems(point_layer_list_name)
        self.dlg.comboBox_point3.addItems(point_layer_list_name)
        self.dlg.comboBox_point4.addItems(point_layer_list_name)
        self.dlg.comboBox_point5.addItems(point_layer_list_name)
        
    
    def click(self):
        
        # Check whether input is not null
        
        # Check input 1
        if self.dlg.comboBox_image1.currentIndex() == 0:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: input image is empty")
            self.set_input()
            return
        if self.dlg.comboBox_point1.currentIndex() == 0:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: input point is empty")
            self.set_input()
            return
        if self.dlg.lineEdit_dataname1.text() == "":
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Data name is null")
            self.set_input()
            return
        if self.dlg.lineEdit.text() == "":
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Output name is null")
            self.set_input()
            return
        
        # Check output
        outputfilename = self.dlg.lineEdit.text()
        if os.path.isfile(outputfilename) == True:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Output file already exist")
            self.set_input()
            return
        outputdir = os.path.dirname(outputfilename)
        if (os.path.isdir(outputdir) == False) or (os.path.exists(outputdir) == False):
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Output directory not exist")
            self.set_input()
            return
        
        
        # Check input 2-5, determine number of process dates
        if (self.dlg.comboBox_image2.currentIndex() > 0) and (self.dlg.comboBox_point2.currentIndex() > 0) and (self.dlg.lineEdit_dataname1.text() != ""):
            if (self.dlg.comboBox_image3.currentIndex() > 0) and (self.dlg.comboBox_point3.currentIndex() > 0) and (self.dlg.lineEdit_dataname3.text() != ""):
                if (self.dlg.comboBox_image4.currentIndex() > 0) and (self.dlg.comboBox_point4.currentIndex() > 0) and (self.dlg.lineEdit_dataname4.text() != ""):
                    if (self.dlg.comboBox_image5.currentIndex() > 0) and (self.dlg.comboBox_point5.currentIndex() > 0) and (self.dlg.lineEdit_dataname5.text() != ""):
                        process_date = 5
                    else:
                        process_date = 4
                else:
                    process_date = 3
            else:
                process_date = 2
        else:
            process_date = 1
              
        can_run = True
        if can_run:
        
            # Fetch the currently loaded layers
            # layers = QgsProject.instance().layerTreeRoot().children()
            layer_list = []
            # layers = QgsProject.instance().mapLayers().values()
            for layer in QgsProject.instance().mapLayers().values():
                layer_list.append(layer)
        
            # Populate names of all the loaded layers
            raster_layer_list = []
            for layer in layer_list:
                if ( layer.type() == layer.RasterLayer ):
                    raster_layer_list.append(layer)       
            point_layer_list = []
            for layer in layer_list:
                if ( layer.type() == layer.VectorLayer ) and ( layer.geometryType() == QgsWkbTypes.PointGeometry ):
                    point_layer_list.append(layer)
 
            # Get raster layer, point layer & data name from combobox
            # QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", str(raster_layer_list))
            # QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", str(self.dlg.comboBox_image1.currentIndex()))
            raster_layer1 = raster_layer_list[self.dlg.comboBox_image1.currentIndex()-1]
            point_layer1 = point_layer_list[self.dlg.comboBox_point1.currentIndex()-1]
            data_name1 = self.dlg.lineEdit_dataname1.text()
            
            process_string = "1. Dataset name: " + str(data_name1) + "; Image: " + str(raster_layer1) + "; Point: " + str(point_layer1) + "\n"
            
            if process_date > 1:
                raster_layer2 = raster_layer_list[self.dlg.comboBox_image2.currentIndex()-1]
                point_layer2 = point_layer_list[self.dlg.comboBox_point2.currentIndex()-1]
                data_name2 = self.dlg.lineEdit_dataname2.text()
                process_string += "2. Dataset name: " + str(data_name2) + "; Image: " + str(raster_layer2) + "; Point: " + str(point_layer2) + "\n"
            if process_date > 2:
                raster_layer3 = raster_layer_list[self.dlg.comboBox_image3.currentIndex()-1]
                point_layer3 = point_layer_list[self.dlg.comboBox_point3.currentIndex()-1]
                data_name3 = self.dlg.lineEdit_dataname3.text()
                process_string += "3. Dataset name: " + str(data_name3) + "; Image: " + str(raster_layer3) + "; Point: " + str(point_layer3) + "\n"
            if process_date > 3:
                raster_layer4 = raster_layer_list[self.dlg.comboBox_image4.currentIndex()-1]
                point_layer4 = point_layer_list[self.dlg.comboBox_point4.currentIndex()-1]
                data_name4 = self.dlg.lineEdit_dataname4.text()
                process_string += "4. Dataset name: " + str(data_name4) + "; Image: " + str(raster_layer4) + "; Point: " + str(point_layer4) + "\n"
            if process_date > 4:
                raster_layer5 = raster_layer_list[self.dlg.comboBox_image5.currentIndex()-1]
                point_layer5 = point_layer_list[self.dlg.comboBox_point5.currentIndex()-1]
                data_name5 = self.dlg.lineEdit_dataname5.text()
                process_string += "5. Dataset name: " + str(data_name5) + "; Image: " + str(raster_layer5) + "; Point: " + str(point_layer5) + "\n"
            
            if self.dlg.checkBox_crs.isChecked() == True:
                if raster_layer1.crs().authid() != point_layer1.crs().authid():
                    QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                        "Error: Different Coordinate Reference System (CRS) for raster & point layers in dataset 1 \n (Right click layers -> properties -> infomation/source to check the layer CRS)")
                    self.set_input()
                    return
                if process_date > 1:
                    if raster_layer2.crs().authid() != point_layer2.crs().authid():
                        QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                            "Error: Different Coordinate Reference System (CRS) for raster & point layers in dataset 2 \n (Right click layers -> properties -> infomation/source to check the layer CRS)")
                        self.set_input()
                        return               
                if process_date > 2:
                    if raster_layer3.crs().authid() != point_layer3.crs().authid():
                        QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                            "Error: Different Coordinate Reference System (CRS) for raster & point layers in dataset 3 \n (Right click layers -> properties -> infomation/source to check the layer CRS)")
                        self.set_input()
                        return    
                if process_date > 3:
                    if raster_layer4.crs().authid() != point_layer4.crs().authid():
                        QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                            "Error: Different Coordinate Reference System (CRS) for raster & point layers in dataset 4 \n (Right click layers -> properties -> infomation/source to check the layer CRS)")
                        self.set_input()
                        return    
                if process_date > 4:
                    if raster_layer5.crs().authid() != point_layer5.crs().authid():
                        QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                            "Error: Different Coordinate Reference System (CRS) for raster & point layers in dataset 5 \n (Right click layers -> properties -> infomation/source to check the layer CRS)")
                        self.set_input()
                        return
            
            # All check pass, Print details of process
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "The tool will run on " + str(process_date) + " datasets: \n " + process_string)        
            
            # Create temp folder
            while True:
                temp = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
                if os.path.isdir(os.path.join(outputdir, temp)) == False:
                    tempdir = os.path.join(outputdir, temp)
                    os.mkdir(tempdir)
                    break
            
            # Define extract point to average function
            def extract_point_to_average(point_layer, raster_layer, data_name, tempcsv_file):
                # Extract raster values
                tempcsv = processing.run("qgis:rastersampling", {'INPUT': point_layer,'RASTERCOPY': raster_layer,
                    'COLUMN_PREFIX': 'rvalue', 'OUTPUT': os.path.join(tempdir, tempcsv_file)})
                # Calculate average
                with open(list(tempcsv.values())[0], 'r') as f:
                    rows = csv.reader(f)
                    i=1
                    b1, b2, b3, b4, b5, b6, b7, b8 = ([] for j in range(8))
                    for row in rows:
                        if i > 1:
                            b1.append(float(row[1]))
                            b2.append(float(row[2]))
                            b3.append(float(row[3]))
                            b4.append(float(row[4]))
                            b5.append(float(row[5]))
                            b6.append(float(row[6]))
                            b7.append(float(row[7]))
                            b8.append(float(row[8]))
                        i += 1
                # Combine data name & average of 8 bands
                ave_list = [data_name]
                for band in [b1, b2, b3, b4, b5, b6, b7, b8]:
                    ave_list.append(round(sum(band)/len(band)/2047,4))
                return (np.array(ave_list))

            # Calculate results for different data & combine to 1 np array
            result1 = extract_point_to_average(point_layer1, raster_layer1, data_name1, "tempresult1.csv")
            if process_date > 1:
                result2 = extract_point_to_average(point_layer2, raster_layer2, data_name2, "tempresult2.csv")
                multidata_np = np.column_stack((result1, result2))
            else:
                multidata_np = result1[np.newaxis].T
            if process_date > 2:
                result3 = extract_point_to_average(point_layer3, raster_layer3, data_name3, "tempresult3.csv")
                multidata_np = np.column_stack((multidata_np, result3))
            if process_date > 3:
                result4 = extract_point_to_average(point_layer4, raster_layer4, data_name4, "tempresult4.csv")
                multidata_np = np.column_stack((multidata_np, result4))
            if process_date > 4:
                result5 = extract_point_to_average(point_layer5, raster_layer5, data_name5, "tempresult5.csv")
                multidata_np = np.column_stack((multidata_np, result5))
            
            # Save np array to txt
            np.savetxt(outputfilename, multidata_np, delimiter=",", fmt='%s')
            
            # Delete temp folder
            shutil.rmtree(tempdir)
            
            # Finish
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Finished extract tree values")

    def set_input_pansharp(self):
        # Clear the contents of the comboBox from previous runs & add methods
        self.dlg.comboBox_method.clear()
        method_list = ["Local Mean and Variance Matching (LMVM)", "Simple RCS", "Bayesian fusion"]
        self.dlg.comboBox_method.addItems(method_list)
    
    def select_output_tif(self):
        filename, _filter = QFileDialog.getSaveFileName(self.dlg, "Select output file","", '*.tif')
        self.dlg.lineEdit_sharp.setText(filename)
    
    def select_toolbox(self):
        filename = QFileDialog.getExistingDirectory(self.dlg, "Select Orfeo Toolbox directory")
        self.dlg.lineEdit_toolbox.setText(filename)    
        
    def select_mul(self):
        filename, _filter = QFileDialog.getOpenFileName(self.dlg, "Select multispectral file")
        self.dlg.lineEdit_mul.setText(filename)   

    def select_pan(self):
        filename, _filter = QFileDialog.getOpenFileName(self.dlg, "Select panchromatic file")
        self.dlg.lineEdit_pan.setText(filename)   

    def click_pansharp(self):

        # Check input
        # Orfeo toolbox
        toolbox_path = self.dlg.lineEdit_toolbox.text()
        if (os.path.isdir(toolbox_path) == False) or (os.path.exists(toolbox_path) == False):
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Toolbox directory not available. \n Please check the folder path.")
            self.set_input_pansharp()
            return
        superimpose_tool_path = os.path.join(toolbox_path, "bin/otbcli_Superimpose.bat")
        pansharp_tool_path = os.path.join(toolbox_path, "bin/otbcli_Pansharpening.bat")
        if (os.path.isfile(superimpose_tool_path) == False) or (os.path.isfile(pansharp_tool_path) == False):
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Required component in toolbox directory not found. \n Please check the toolbox folder or download again.")
            self.set_input_pansharp()
            return
        
        # input mul
        mul_path = self.dlg.lineEdit_mul.text()
        mul_layer = QgsRasterLayer(mul_path, "multispectral")
        if not mul_layer.isValid():
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Input multispectral image cannot be loaded")
            self.set_input_pansharp()
            return
        
        # input pan
        pan_path = self.dlg.lineEdit_pan.text()
        pan_layer = QgsRasterLayer(pan_path, "panchromatic")
        if not pan_layer.isValid():
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Input panchromatic image cannot be loaded")
            self.set_input_pansharp()
            return

        # Check output
        outputfilename = self.dlg.lineEdit_sharp.text()
        if os.path.isfile(outputfilename) == True:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Output file already exist")
            self.set_input_pansharp()
            return
        outputdir = os.path.dirname(outputfilename)
        if (os.path.isdir(outputdir) == False) or (os.path.exists(outputdir) == False):
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Output directory not exist")
            self.set_input_pansharp()
            return
        
        # Check CRS of input
        if mul_layer.crs().authid() != pan_layer.crs().authid():
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                "Error: Different Coordinate Reference System (CRS) for multispectral & panchromatic images \n (Right click layers -> properties -> infomation/source to check the layer CRS)")
            self.set_input_pansharp()
            return
            
        # Check pixel size & extent of input
        if mul_layer.rasterUnitsPerPixelX() <= pan_layer.rasterUnitsPerPixelX():
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                "Error: Multispectral image should have larger pixel size (e.g. 2 m) than panchromatic image (e.g. 0.5 m)")
            self.set_input_pansharp()
            return
        if mul_layer.extent() != pan_layer.extent():
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", 
                "Error: Different extent for multispectral & panchromatic images")
            self.set_input_pansharp()
            return
        
        # All check OK, can proceed
        
        # Pansharpening method
        method_list_otb = ["lmvm", "rcs", "bayes"]
        pansharp_method = method_list_otb[self.dlg.comboBox_method.currentIndex()]
        
        # temp superimpose output name
        while True:
            temp = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
            tempsuperimpose = os.path.join(outputdir, "tempsuperimpose" + temp + ".tif")
            tempsuperimpose_geom = os.path.join(outputdir, "tempsuperimpose" + temp + ".geom")
            if os.path.exists(tempsuperimpose) == False:
                break         
        
        # superimpose
        os.system(superimpose_tool_path + " -inr " + pan_path + " -inm " + mul_path + " -out " + tempsuperimpose)
        
        # pansharpening
        os.system(pansharp_tool_path + " -inp " + pan_path + " -inxs " + tempsuperimpose + " -out " + outputfilename + " uint16" + " -method " + pansharp_method)
        
        # remove superimpose image
        os.remove(tempsuperimpose)
        if os.path.exists(tempsuperimpose_geom) == True:
            os.remove(tempsuperimpose_geom)
        out_basename, ext = os.path.splitext(outputfilename)
        out_geom = out_basename + ".geom"
        if os.path.exists(out_geom) == True:
            os.remove(out_geom)
            
        # load layer if checked
        if self.dlg.checkBox_load.isChecked() == True:
            sharp_name = os.path.basename(outputfilename)
            sharp_layer = QgsRasterLayer(outputfilename, sharp_name)
            QgsProject.instance().addMapLayer(sharp_layer)
        
        QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Finished image pansharpening")


    def refresh_raster(self):
        # Clear the contents of the comboBox from previous runs
        self.dlg.comboBox_targetlayer.clear()
        self.dlg.comboBox_referenceimage.clear()
    
        # Fetch the currently loaded layers
        layer_list = []
        for layer in QgsProject.instance().mapLayers().values():
            layer_list.append(layer)
    
        # Populate the comboBox with names of all the loaded layers
        raster_layer_list = []
        for layer in layer_list:
            if ( layer.type() == layer.RasterLayer ):
                raster_layer_list.append(layer)       
        
        raster_layer_list_name2 = [layer.name() for layer in raster_layer_list]
        
        # Add name to combobox
        self.dlg.comboBox_targetlayer.addItems(raster_layer_list_name2)
        self.dlg.comboBox_referenceimage.addItems(raster_layer_list_name2)
        	
    def changetorgb(self):
        targetlayer_name = str(self.dlg.comboBox_targetlayer.currentText())
        targetlayer = QgsProject.instance().mapLayersByName(targetlayer_name)[0]
        if targetlayer == []:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Image cannnot be found")
            self.refresh_raster()
            return
        if targetlayer.bandCount() < 8:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: The image is not a 8-band WorldView data")
            self.refresh_raster()
            return
        targetlayer.renderer().setRedBand(5)
        targetlayer.renderer().setGreenBand(3)
        targetlayer.renderer().setBlueBand(2)
        targetlayer.setContrastEnhancement(QgsContrastEnhancement.StretchToMinimumMaximum, QgsRasterMinMaxOrigin.CumulativeCut)
        targetlayer.triggerRepaint()

    def changetonir(self):
        targetlayer_name = str(self.dlg.comboBox_targetlayer.currentText())
        targetlayer = QgsProject.instance().mapLayersByName(targetlayer_name)[0]
        if targetlayer == []:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Image cannnot be found")
            self.refresh_raster()
            return
        if targetlayer.bandCount() < 8:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: The image is not a 8-band WorldView data")
            self.refresh_raster()
            return
        targetlayer.renderer().setRedBand(7)
        targetlayer.renderer().setGreenBand(5)
        targetlayer.renderer().setBlueBand(3)
        targetlayer.setContrastEnhancement(QgsContrastEnhancement.StretchToMinimumMaximum, QgsRasterMinMaxOrigin.CumulativeCut)
        targetlayer.triggerRepaint()    

    def select_output_point(self):
        filename, _filter = QFileDialog.getSaveFileName(self.dlg, "Select output file","", '*.gpkg')
        self.dlg.lineEdit_point.setText(filename)
    
    def click_point(self):
        
        # Check input (reference image)
        refimage_name = str(self.dlg.comboBox_referenceimage.currentText())
        refimage = QgsProject.instance().mapLayersByName(refimage_name)[0]        
        if refimage == []:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Reference image cannnot be found")
            self.refresh_raster()
            return        
        
        # Check output
        outputfilename = self.dlg.lineEdit_point.text()
        if os.path.exists(outputfilename) == True:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Output file already exist")
            self.refresh_raster()
            return
        outputdir = os.path.dirname(outputfilename)
        if (os.path.isdir(outputdir) == False) or (os.path.exists(outputdir) == False):
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Output directory not exist")
            self.refresh_raster()
            return
        
        # Check OK, can run
        
        vl = QgsVectorLayer("Point", "temporary_points", "memory")
        vl.setCrs(refimage.crs())
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        transform_context = QgsProject.instance().transformContext()
        error = QgsVectorFileWriter.writeAsVectorFormatV2(vl, outputfilename, transform_context, save_options)
        
        if error[0] != QgsVectorFileWriter.NoError:
            QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Cannot create point gpkg file")
            self.refresh_raster()
            return

        # Show in project
        if self.dlg.checkBox_load_point.isChecked() == True:
            vlayer = self.iface.addVectorLayer(outputfilename, "", "ogr")
            if not vlayer:
                QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Error: Cannot load point layer")   
                self.refresh_raster()                
                return

        QMessageBox.information(self.dlg, "GIC Tree Monitoring Tool", "Finished create point layer")  
   
    def close(self):
        self.dlg.close()

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            # self.first_start = False
            self.dlg = GICTreeMonitoringToolDialog()
            # link push button to fuctions
            # extract values
            self.dlg.pushButton.clicked.connect(self.select_output_file)
            self.dlg.pushButton_clear.clicked.connect(self.set_input)
            # pansharp
            self.dlg.pushButton_mul.clicked.connect(self.select_mul)
            self.dlg.pushButton_pan.clicked.connect(self.select_pan)
            self.dlg.pushButton_toolbox.clicked.connect(self.select_toolbox)
            self.dlg.pushButton_sharp.clicked.connect(self.select_output_tif)
            # colour
            self.dlg.pushButton_refresh.clicked.connect(self.refresh_raster)
            self.dlg.pushButton_changetorgb.clicked.connect(self.changetorgb)
            self.dlg.pushButton_changetonir.clicked.connect(self.changetonir)
            # point
            self.dlg.pushButton_refresh2.clicked.connect(self.refresh_raster)
            self.dlg.pushButton_point.clicked.connect(self.select_output_point)
            # when OK button is clicked
            self.dlg.pushButton_run.clicked.connect(self.click)
            self.dlg.pushButton_run_pansharp.clicked.connect(self.click_pansharp)
            self.dlg.pushButton_run_point.clicked.connect(self.click_point)
            # when close button is clicked
            self.dlg.pushButton_close.clicked.connect(self.close)
            self.dlg.pushButton_close_pansharp.clicked.connect(self.close)
            self.dlg.pushButton_close_colour.clicked.connect(self.close)
            self.dlg.pushButton_close_point.clicked.connect(self.close)
            
		           
        self.set_input()
        self.set_input_pansharp()
        self.refresh_raster()
        self.dlg.checkBox_crs.setChecked(1)
        self.dlg.checkBox_load.setChecked(1)
        self.dlg.checkBox_load_point.setChecked(1)

        # show the dialog
        self.dlg.show()
        # result = self.dlg.exec_()


			
			
			
