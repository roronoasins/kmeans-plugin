# -*- coding: utf-8 -*-
"""
/***************************************************************************
 KMeansDialog
                                 A QGIS plugin
 This plugin is a minimal plugin that uses K-Means algorithm to group locations based in features.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2020-12-16
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Luis González
        email                : luisgonromero@correo.ugr.es
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

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.core import *

from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.gui import QgsFieldComboBox
from qgis.utils import iface
from PyQt5.QtCore import QVariant

import random
import math
import time

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'KM_dialog_base.ui'))



class KMeansDialog(QtWidgets.QDialog, FORM_CLASS):
    def select_output_file(self):
        filename, _filter = QFileDialog.getSaveFileName(self, "Select   output file ","", '*.shp')
        self.outputLineEdit.setText(filename)

    def apply_kmeans(self):
        # get k value
        k = int(self.kLineEdit.text())
        #string = "Segmenting data with " + str(k) + " clusters"
        #QgsMessageLog.logMessage(string, 'K-Means plugin', level=Qgis.Info)
        layers = QgsProject.instance().layerTreeRoot().children()
        
        #selected field
        selectedField = self.fieldComboBox.currentField()
        #selectedLayer = layers[self.comboBox.currentIndex()].layer()
        selectedLayer = self.comboBox.currentLayer()
        layerName = selectedLayer.name()
        mss = "running k-means algorithm based in "+selectedField+"from "+layerName+" in "+str(k)+" clusters."
        QgsMessageLog.logMessage(mss, 'K-Means plugin', level=Qgis.Info)

        
        features = selectedLayer.getFeatures()
        result = QgsProject.instance().mapLayersByName(selectedLayer.name())[0]
        r_prov = result.dataProvider()
        #QgsMessageLog.logMessage(field, 'K-Means plugin', level=Qgis.Info)
        #self.fieldsTable = self.tableWidget
        f = 0
        attrs = []
        for feat in features:
            f+=1
            #QgsMessageLog.logMessage(feat, 'K-Means plugin', level=Qgis.Info)
            attrs.append(feat.attributes())

        x = 0
        casos = []
        ccaa = []
        for feat in attrs:
            for attributes in feat:
                if x == 1:
                    ccaa.append(attributes)
                if x == 5:
                    #QgsMessageLog.logMessage(i, 'K-Means plugin', level=Qgis.Info)
                    casos.append(attributes)
                x+=1
            x = 0
        #QgsMessageLog.logMessage(str(f), 'K-Means plugin', level=Qgis.Info)
        #QgsMessageLog.logMessage(str(len(attrs)), 'K-Means plugin', level=Qgis.Info)
        etiquetas, comunidades = self.clustering(ccaa, casos, k)
        eti = []
        for i in range(k):
            eti.append([])
            strk = "Etiquetas para k = "+str(i)
            QgsMessageLog.logMessage(strk, 'K-Means plugin', level=Qgis.Info)
            for j in range(len(etiquetas)):
                if etiquetas[j] == i:
                    eti[i].append(comunidades[j])
                    #QgsMessageLog.logMessage(comunidades[j], 'K-Means plugin', level=Qgis.Info)
            listToStr = ' '.join([str(elem) for elem in eti[i]])
            QgsMessageLog.logMessage(listToStr, 'K-Means plugin', level=Qgis.Info)

        # añadir las etiquetas como nuevo campo
        #selectedLayer = layers[self.comboBox.currentIndex()].layer()
        self.createLabels(selectedLayer)
        self.updateLabels(etiquetas, selectedLayer)
        colors = self.createColors(k, selectedLayer)
        self.updateColors(colors,selectedLayer)
        
        self.close()
        return

    # create label in field table
    def createLabels(self, layer):
        layer_provider = layer.dataProvider()
        layer_provider.addAttributes([QgsField("etiquetas",QVariant.Int)])
        layer.updateFields()
        #QgsMessageLog.logMessage(layer.name(), 'K-Means plugin', level=Qgis.Info)
        
    # update labels value in field table
    def updateLabels(self, labels, layer):
        i = 0
        with edit(layer):
            for f in layer.getFeatures():
                f['etiquetas'] = labels[i]
                i += 1
                layer.updateFeature(f)
        return

    # generate random hex/rgb colors based in k and create color field
    def createColors(self, k, layer):
        colors = []
        for i in range(k):
            random_number = random.randint(0,16777215)
            hex_number = str(hex(random_number))
            hex_number ='#'+ hex_number[2:]
            colors.append(hex_number)

        layer_provider = layer.dataProvider()
        layer_provider.addAttributes([QgsField("color",QVariant.String)])
        layer.updateFields()
        
        return colors

    # update color vale in field table based in which label the ccaa has
    def updateColors(self, colors, layer):
        i = 0
        with edit(layer):
            for f in layer.getFeatures():
                f['color'] = colors[f['etiquetas']]
                i += 1
                layer.updateFeature(f)
        return

    def clustering(self, comunidades, casos, k):
        clusters = []
        for i in range(k):
            clusters.append([])

        instancias = comunidades.copy()
        random.shuffle(instancias)
        labels = [0] * len(instancias)
        #solucion inicial
        for i in range(len(instancias)):
            random_k = random.randrange(0,k)
            labels[i] = random_k
            clusters[random_k].append(i)
        # actualizamos centroides
        centroides = self.get_centroides(clusters, k)
        #actualizar labels
        mejora = True
        while mejora:
            mejora = False
            for i in range(len(instancias)):
                #QgsMessageLog.logMessage(str(i), 'K-Means plugin', level=Qgis.Info)
                old_f = self.f(centroides, clusters)
                old_cluster = labels[i]
                new_cluster = random.randrange(0,k)
                while new_cluster == old_cluster:
                    new_cluster = random.randrange(0,k)
                labels[i] = new_cluster
                clusters[old_cluster].remove(i)
                clusters[new_cluster].append(i)

                new_f = self.f(centroides, clusters)
                if new_f > old_f:
                    labels[i] = old_cluster
                    clusters[new_cluster].remove(i)
                    clusters[old_cluster].append(i)
                else:
                    mejora = True

        QgsMessageLog.logMessage("k-means has finished correctly", 'K-Means plugin', level=Qgis.Info)
        return labels, instancias
                
    def get_centroides(self, clusters, k):
        cen = [0] * k
        for k in range(len(clusters)):
            suma = 0
            for i in range(len(clusters[k])):
                suma += i
            suma /= len(clusters[k])
            cen[k] = suma
        return cen

    def f(self, centroides, clusters):
        f = 0
        for k in range(len(clusters)):
            #QgsMessageLog.logMessage(str(clusters[k]), 'K-Means plugin', level=Qgis.Info)
            for i in range(len(clusters[k])):
                f += math.pow(abs(clusters[k][i] - centroides[k]), 2)
        return f

    def progress_bar(self):
        #self.progressBar.setValue(self.progressBar.value()+1) #Progress Bar
        return
        
    
    def __init__(self, parent=None):
        """Constructor."""
        super(KMeansDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        # Fetch the currently loaded layers
        layers = QgsProject.instance().layerTreeRoot().children()
 
        self.comboBox.layerChanged.connect(self.fieldComboBox.setLayer)
        self.fieldComboBox.setLayer(self.comboBox.currentLayer())

        #pb = self.progressBar
        #pb.setValue(0)
        #pb.setRange(0,100)
        
        self.outputButton.clicked.connect(self.select_output_file)
        self.applyButton.clicked.connect(self.apply_kmeans)

        
